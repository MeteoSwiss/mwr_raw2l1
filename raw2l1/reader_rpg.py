# -*- coding: utf-8 -*-
"""
reader for RPG HATPRO, TEMPRO or HUMPRO binary files
"""
import numpy as np
import datetime as dt
import struct
import os
from errors import UnknownFileType, FileTooShort

# configuration to be exported to config file
missing_float = -999.
missing_int = -9

BYTE_ORDER = '<'  # byte order in all RPG files assumed little-endian  #TODO: ask Harald whether this is true or whether it depends on the instrument PC (hopefully not!)

FILETYPE_CONFS = {  # assign metadata to each known filecode
    # BRT files
    666666: dict(type='brt', anglever=1, formatchar_angle='f'),
    666667: dict(type='brt', anglever=1, formatchar_angle='f'),
    666000: dict(type='brt', anglever=2, formatchar_angle='i'),
    667000: dict(type='brt', anglever=2, formatchar_angle='i'),
    # BLB files
    567845847: dict(type='blb', structver=1),
    567845848: dict(type='blb', structver=2),
    # IRT files
    671112495: dict(type='irt', structver=1),
    671112496: dict(type='irt', structver=2, anglever=1, formatchar_angle='f'),
    671112000: dict(type='irt', structver=2, anglever=2, formatchar_angle='i'),
    # MET files
    599658943: dict(type='met', structver=1),
    599658944: dict(type='met', structver=2),
    # HKD files
    837854832: dict(type='hkd'),
}
# TODO: ask Volker whether different dict structures are ok here



###############################################################################
# readers for different RPG files
# ------------------------------------------------------------------------------

def get_binary(filename):
    """return the entire content of the binary file as binary stream"""
    with open(filename, 'rb') as f:
        return f.read()
# TODO: ask Volker if it is ok to declare get_binary outside of any class (pretty general in my eyes). If yes, should it go to helper functions module

class BaseFile(object):
    def __init__(self, filename, accept_localtime=False):
        self.filename = filename
        self.data = {}
        self.byte_offset = 0  # counter for consumed bytes, increased by each method
        self.filecode = None
        self.filestruct = None
        self.data_bin = get_binary(self.filename)
        self.read()  # fills self.data
        self.check_data(accept_localtime)

    def read(self):
        # sequence must be preserved as self.byte_offset is increased by each method, hence they are all semi-private
        # TODO: ask Volker whether this semi-private makes sense
        self._read_filecode()
        self.interpret_filecode()
        self._read_header()
        self._read_meas()
        self.interpret_raw_data()

    def decode_binary(self, encoding_pattern, byte_order=BYTE_ORDER):
        """"decode next variable from binary stream and write to dict self.data + augment self.byte_offset"""
        full_type = byte_order + encoding_pattern['shape'][0] * encoding_pattern['type']
        out = struct.unpack_from(full_type, self.data_bin, self.byte_offset)
        self.byte_offset += encoding_pattern['bytes']
        if len(out) == 1:  # extract from tuple if it has only one element, otherwise return tuple
            self.data[encoding_pattern['name']] = out[0]
        else:
            self.data[encoding_pattern['name']] = out

    def decode_binary_np(self, encoding_pattern, n_entries, byte_order=BYTE_ORDER):
        """decode bunch of binary stream via 2d numpy array to write to dict self.data + augment self.byte_offset"""
        dtype_np = np.dtype([(ep['name'], byte_order+ep['type'], ep['shape']) for ep in encoding_pattern])
        names = [ep['name'] for ep in encoding_pattern]
        bytes_per_var = np.array([ep['bytes'] for ep in encoding_pattern])

        byte_offset_start = self.byte_offset
        n_bytes = bytes_per_var.sum() * n_entries
        self.byte_offset += n_bytes
        if len(self.data_bin) < self.byte_offset:  # TODO: ask Volker if check is ok here. think I can't check earlier
            raise FileTooShort('number of bytes in file %s does not match the one inferred from n_meas' % self.filename)

        arr = np.frombuffer(self.data_bin[byte_offset_start: self.byte_offset], dtype=dtype_np)
        for idx, name in enumerate(names):
            if encoding_pattern[idx]['shape'] == (1,):  # variables which only have a time dimension shall not be 2d
                self.data[name] = arr[name].flatten()  # TODO: ask Volker if this manipulation is ok. Doing this also for later usage in loops
            else:
                self.data[name] = arr[name]

    def interpret_filecode(self):
        try:
            self.filestruct = FILETYPE_CONFS[self.filecode]
        except KeyError:
            raise UnknownFileType('reader not specified for files with filecode %d as used in %s'
                                  % (self.filecode, self.filename))

    def interpret_raw_data(self):
        self.data['time'] = interpret_time(self.data['time_raw'])
        if 'pointing_raw' in self.data.keys():
            self.data['ele'], self.data['azi'] = interpret_angle(self.data['pointing_raw'], self.filestruct['anglever'])

    def check_data(self, accept_localtime):
        if not accept_localtime and self.data['timeref'] == 0:
            raise ValueError('Time encoded in local time but UTC required by "accept_localtime"')
            # TODO: Ask Volker if it is ok to raise a ValueError here or if we should define own error type

    def _read_filecode(self):
        """first of the _read... methods to be executed (according to order in file)"""
        self.filecode = struct.unpack_from('<i', self.data_bin, self.byte_offset)[0]
        self.byte_offset += 4

    def _read_header(self):
        """second of the _read... methods to be executed (according to order in file)"""
        pass

    def _read_meas(self):
        """third of the _read... methods to be executed (according to order in file)"""
        pass


class BRT(BaseFile):
    # TODO: Ask Volker how to enhance inherited method interpret_filecode with check that filecode corresponds to BRT
    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = (
            dict(name='n_meas', type='i', shape=(1,), bytes=4),
            dict(name='timeref', type='i', shape=(1,), bytes=4),
            dict(name='n_freq', type='i', shape=(1,), bytes=4))
        for enc in encodings_bin_fix:
            self.decode_binary(enc)

        # quantities with length-dependent on number of spectral channels (n_freq) only possible after n_freq is read
        n_freq = self.data['n_freq']
        encodings_bin_var = (
            dict(name='frequency', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_min', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_max', type='f', shape=(n_freq,), bytes=n_freq * 4))
        for enc in encodings_bin_var:
            self.decode_binary(enc)

    def _read_meas(self):
        """read actual measurements. Filecode and Header needs to be read before as info is needed for decoding"""
        n_freq = self.data['n_freq']
        encodings_bin = (
            dict(name='time_raw', type='i', shape=(1,), bytes=4),
            dict(name='rainflag', type='B', shape=(1,), bytes=1),
            dict(name='Tb', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='pointing_raw', type=self.filestruct['formatchar_angle'], shape=(1,), bytes=4))
        self.decode_binary_np(encodings_bin, self.data['n_meas'])


# TODO: Consider transforming to SI units. IRT -> K; wavelength -> m; frequency -> Hz
def read_brt(filename, accept_localtime=False):
    """
    Read BRT file holding the MWR brightness temperatures of starring obs
    (fixed azimuth and elevation)

    Parameters
    ----------
    filename : str
        path to *.brt file holding the starring MWR brightness temp obs.
    accept_localtime : bool, optional
        Accept that timestamp is stored in localtime. The default is False.


    Returns
    -------
    data : dict
        containts observations and metadata
        flag meanings:
            rainflag: 0, no rain; 1, rain
    """

    with open(filename, 'rb') as f:
        d = f.read()

    data = {}
    byte_offset = 0  # counter for consumed bytes

    # header info
    #############

    # read and check file code
    data['filecode'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if data['filecode'] == 666666 or data['filecode'] == 666667:
        anglever = 1
        formatchar_angle = 'f'
    elif data['filecode'] == 666000 or data['filecode'] == 667000:
        anglever = 2
        formatchar_angle = 'i'
    else:
        raise ValueError('Unknown file format. Known codes for BRT files are '
                         + '666666, 666667, 666000 or 667000 but received %d' % data['filecode'])

        # read rest of header info
    data['n_meas'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['timeref'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['n_freq'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['frequency'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4
    data['Tb_min'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4
    data['Tb_max'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4

    # tests on header
    if not accept_localtime and data['timeref'] == 0:
        raise ValueError('Time encoded in local time but UTC required by "accept_localtime"')

        # measurements
    ##############

    # init measurements
    data['time'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['rainflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['Tb'] = np.ones((data['n_meas'], data['n_freq']), dtype=np.float32) * missing_float
    data['ele'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['azi'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float

    # read measurements
    for n in range(data['n_meas']):
        data['time'][n] = interpret_time(struct.unpack_from('<i', d, byte_offset)[0])
        byte_offset += 4
        data['rainflag'][n] = struct.unpack_from('<B', d, byte_offset)[0]
        byte_offset += 1
        data['Tb'][n] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
        byte_offset += data['n_freq'] * 4
        data['ele'][n], data['azi'][n] = interpret_angle(struct.unpack_from(
            '<' + formatchar_angle, d, byte_offset)[0], anglever)
        byte_offset += 4

    return data


def read_blb(filename, accept_localtime=False):
    """
    Read BLB file holding the MWR brightness temperatures of elevation scans

    Parameters
    ----------
    filename : str
        path to *.blb file holding the scanning observations.
    accept_localtime : bool, optional
        Accept that timestamp is stored in localtime. The default is False.


    Returns
    -------
    data : dict
        containts observations and metadata
        flag meanings:
            rainflag: 0, no rain; 1, rain
            scanmode: 0, 1st quadrant; 1, 2nd quadrant; 
                      2, two quadrant avg; 3, two independent scans
    """

    n_freq_default = 14  # used to read in files of structver=1 where spectram comes before n_freq
    # TODO: check how RPG deals with files from TEMPRO or HUMPRO how would have different n_freq. Other filecodes? Could also get frequency info from BRT files but ugly dependency.

    with open(filename, 'rb') as f:
        d = f.read()

    data = {}
    byte_offset = 0  # counter for consumed bytes

    # header info
    #############

    # read and check file code
    data['filecode'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if data['filecode'] == 567845847:
        structver = 1
    elif data['filecode'] == 567845848:
        structver = 2
    else:
        raise ValueError(
            'Unknown file format. Known codes for BLB files are 567845847 and 567845848 but received %d' % data[
                'filecode'])

        # read rest of header info
    data['n_scans'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if structver >= 2:
        data['n_freq'] = struct.unpack_from('<i', d, byte_offset)[0]
        byte_offset += 4
    else:
        data['n_freq'] = n_freq_default  # no byte offset here as not reading from file
    data['Tb_min'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4
    data['Tb_max'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4
    data['timeref'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if structver == 1:  # n_freq already assumed for reading in previous spectra, check whether this was correct
        n_freq_file = struct.unpack_from('<i', d, byte_offset)[0]
        byte_offset += 4
        if n_freq_file != data['n_freq']:
            raise ValueError('Assumed wrong number of frequency channels for reading in BLB header')
    data['frequency'] = struct.unpack_from('<' + data['n_freq'] * 'f', d, byte_offset)
    byte_offset += data['n_freq'] * 4
    data['n_ele'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['scan_ele'] = struct.unpack_from('<' + data['n_ele'] * 'f', d, byte_offset)
    byte_offset += data['n_ele'] * 4

    data['n_meas'] = data['n_scans'] * data['n_ele']

    # measurements
    ##############

    # init measurements
    data['scan_starttime'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['time'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['rainflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['scanmode'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['Tb'] = np.ones((data['n_meas'], data['n_freq']), dtype=np.float32) * missing_float
    data['T'] = np.ones((data['n_meas']), dtype=np.float32) * missing_float
    data['ele'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    # TODO: find a way to infer data['azi']
    single_scan = np.ones((data['n_freq'], data['n_ele'] + 1), dtype=np.float32) * missing_float

    # read measurements. flatten scan in series of time at different azimuth and ele
    for n in range(data['n_scans']):
        i0 = n * data['n_ele']
        i1 = (n + 1) * data['n_ele']

        # write per-scan information to time series
        data['scan_starttime'][i0:i1] = interpret_time(
            struct.unpack_from('<i', d, byte_offset)[0])
        byte_offset += 4
        data['time'][i0:i1] = scan_starttime_to_time(
            data['scan_starttime'][i0], data['n_ele'])  # no byte offset here
        flagbits = np.unpackbits(np.uint8(
            struct.unpack_from('<B', d, byte_offset)[0]), bitorder='little')
        byte_offset += 1
        data['rainflag'][i0:i1] = flagbits[0]
        if structver == 1:
            data['scanmode'][i0:i1] = flagbits[1] + 2 * flagbits[2]
        else:
            data['scanmode'][i0:i1] = flagbits[-2] + 2 * flagbits[-1]
        data['ele'][i0:i1] = data['scan_ele']

        # write observations to time series
        for m in range(data['n_freq']):
            single_scan[m] = struct.unpack_from('<' + (data['n_ele'] + 1) * 'f', d, byte_offset)
            byte_offset += (data['n_ele'] + 1) * 4
        data['Tb'][i0:i1] = single_scan[:, :-1].transpose().copy()  # first n_ele elemts are Tb
        data['T'][i0:i1] = single_scan[
            0, -1].transpose().copy()  # last element is ambient temperature (same for each frequency)

    return data


def read_irt(filename, accept_localtime=False):
    """
    Read IRT file holding the infrared brightness temperatures 

    Parameters
    ----------
    filename : str
        path to *.irt file holding the infrared observations.
    accept_localtime : bool, optional
        Accept that timestamp is stored in localtime. The default is False.


    Returns
    -------
    data : dict
        containts observations and metadata
        flag meanings:
            rainflag: 0, no rain; 1, rain
    """

    with open(filename, 'rb') as f:
        d = f.read()

    data = {}
    byte_offset = 0  # counter for consumed bytes

    # header info
    #############

    # read and check file code
    data['filecode'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if data['filecode'] == 671112495:
        structver = 1
    elif data['filecode'] == 671112496:
        structver = 2
        anglever = 1
        formatchar_angle = 'f'
    elif data['filecode'] == 671112000:
        structver = 2
        anglever = 2
        formatchar_angle = 'i'
    else:
        raise ValueError('Unknown file format. Known codes for IRT files are '
                         + '671112495, 671112496 or 671112000 but received %d' % data['filecode'])

        # read rest of header info
    data['n_meas'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['IRT_min'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['IRT_max'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['timeref'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if structver <= 2:
        data['n_wavelengths'] = struct.unpack_from('<i', d, byte_offset)[0]
        byte_offset += 4
        data['wavelength'] = struct.unpack_from('<' + data['n_wavelengths'] * 'f', d, byte_offset)
        byte_offset += data['n_wavelengths'] * 4
    else:
        data['n_wavelengths'] = 1
        data['n_wavelength'] = missing_float

    # tests on header
    if not accept_localtime and data['timeref'] == 0:
        raise ValueError('Time encoded in local time but UTC required by "accept_localtime"')

        # measurements
    ##############

    # init measurements
    data['time'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['rainflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['IRT'] = np.ones((data['n_meas'], data['n_wavelengths']), dtype=np.float32) * missing_float
    data['ele'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['azi'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float

    # read measurements
    for n in range(data['n_meas']):
        data['time'][n] = interpret_time(struct.unpack_from('<i', d, byte_offset)[0])
        byte_offset += 4
        data['rainflag'][n] = struct.unpack_from('<B', d, byte_offset)[0]
        byte_offset += 1
        data['IRT'][n] = struct.unpack_from('<' + data['n_wavelengths'] * 'f', d, byte_offset)
        byte_offset += data['n_wavelengths'] * 4
        if structver == 2:
            data['ele'][n], data['azi'][n] = interpret_angle(struct.unpack_from(
                '<' + formatchar_angle, d, byte_offset)[0], anglever)
            byte_offset += 4

    return data


def read_met(filename, accept_localtime=False):
    """
    Read MET file holding the observations of the weather sensors 

    Parameters
    ----------
    filename : str
        path to *.met file holding the meteorological observations.
    accept_localtime : bool, optional
        Accept that timestamp is stored in localtime. The default is False.


    Returns
    -------
    data : dict
        containts observations and metadata
        flag meanings:
            rainflag: 0, no rain; 1, rain
    """

    with open(filename, 'rb') as f:
        d = f.read()

    data = {}
    byte_offset = 0  # counter for consumed bytes

    # header info
    #############

    # read and check file code
    data['filecode'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if data['filecode'] == 599658943:
        structver = 1
    elif data['filecode'] == 599658944:
        structver = 2
    else:
        raise ValueError('Unknown file format. Known codes for MET files are '
                         + '599658943 or 599658944 but received %d' % data['filecode'])

        # read rest of header info
    data['n_meas'] = struct.unpack_from('<i', d, byte_offset)[0]  # number of measurements each indivitual sensor took
    byte_offset += 4
    if structver >= 2:  # get list of additional sensors
        auxsensbits = np.unpackbits(np.uint8(
            struct.unpack_from('<B', d, byte_offset)[0]), bitorder='little')
        byte_offset += 1
        data['has_windspeed'] = auxsensbits[0]
        data['has_winddir'] = auxsensbits[1]
        data['has_rainrate'] = auxsensbits[2]
    else:
        data['has_windspeed'] = 0
        data['has_winddir'] = 0
        data['has_rainrate'] = 0  # no byte offset here as not reading from file
    data['p_min'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['p_max'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['T_min'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['T_max'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['RH_min'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    data['RH_max'] = struct.unpack_from('<f', d, byte_offset)[0]
    byte_offset += 4
    if data['has_windspeed']:
        data['windspeed_min'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        data['windspeed_max'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
    else:
        data['windspeed_min'] = missing_float
        data['windspeed_max'] = missing_float
    if data['has_winddir']:
        data['winddir_min'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        data['winddir_max'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
    else:
        data['winddir_min'] = missing_float
        data['winddir_max'] = missing_float
    if data['has_rainrate']:
        data['rainrate_min'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        data['rainrate_max'] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
    else:
        data['rainrate_min'] = missing_float
        data['rainrate_max'] = missing_float
    data['timeref'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4

    # tests on header
    if not accept_localtime and data['timeref'] == 0:
        raise ValueError('Time encoded in local time but UTC required by "accept_localtime"')

        # measurements
    ##############

    # init measurements
    data['time'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['rainflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['p'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['T'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['RH'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['windspeed'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['winddir'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['rainrate'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float

    # read measurements
    for n in range(data['n_meas']):
        data['time'][n] = interpret_time(struct.unpack_from('<i', d, byte_offset)[0])
        byte_offset += 4
        data['rainflag'][n] = struct.unpack_from('<B', d, byte_offset)[0]
        byte_offset += 1
        data['p'][n] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        data['T'][n] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        data['RH'][n] = struct.unpack_from('<f', d, byte_offset)[0]
        byte_offset += 4
        if data['has_windspeed']:
            data['windspeed'] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
        if data['has_winddir']:
            data['winddir'] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
        if data['has_rainrate']:
            data['rainrate'] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4

    return data


def read_hkd(filename, accept_localtime=False):
    """
    Read HKD file holding the housekeeping data

    Parameters
    ----------
    filename : str
        path to *.hkd file holding the housekeeping data.
    accept_localtime : bool, optional
        Accept that timestamp is stored in localtime. The default is False.


    Returns
    -------
    data : dict
        containts observations and metadata
        flag meanings:
            rainflag: 0, no rain; 1, rain
    """

    n_freq_kband = 7  # number of frequency channels in K-band receiver
    n_freq_vband = 7  # number of frequency channels in V-band receiver

    with open(filename, 'rb') as f:
        d = f.read()

    data = {}
    byte_offset = 0  # counter for consumed bytes

    # header info
    #############

    # read and check file code
    data['filecode'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    if data['filecode'] != 837854832:
        raise ValueError('Unknown file format. Known codes for HKD file is '
                         + '837854832 but received %d' % data['filecode'])

        # read rest of header info
    data['n_meas'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    data['timeref'] = struct.unpack_from('<i', d, byte_offset)[0]
    byte_offset += 4
    hkdselbits = statusflagbits = np.unpackbits(
        np.array(struct.unpack_from('<i', d, byte_offset)).view(np.uint8),
        bitorder='little')
    byte_offset += 4
    data['has_coord'] = hkdselbits[0]
    data['has_T'] = hkdselbits[1]
    data['has_stability'] = hkdselbits[2]
    data['has_flashmemoryinfo'] = hkdselbits[3]
    data['has_qualityflag'] = hkdselbits[4]
    data['has_statusflag'] = hkdselbits[5]  # following three bytes of hkdselbits not used

    # tests on header
    if not accept_localtime and data['timeref'] == 0:
        raise ValueError('Time encoded in local time but UTC required by "accept_localtime"')

        # measurement info
    ##################

    # init variables
    data['time'] = np.empty(data['n_meas'], dtype=np.dtype(dt.datetime))
    data['alarm'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['lon'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['lat'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['T_amb_1'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['T_amb_2'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['T_receiver_kband'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['T_receiver_vband'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['Tstab_kband'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['Tstab_vband'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['flashmemory_remaining'] = np.ones(data['n_meas'], dtype=np.float32) * missing_float
    data['L2_qualityflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['channel_quality_ok_kband'] = np.ones((data['n_meas'], n_freq_kband), dtype=np.float32) * missing_float
    data['channel_quality_ok_vband'] = np.ones((data['n_meas'], n_freq_vband), dtype=np.float32) * missing_float
    data['rainflag'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['blowerspeed_status'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['BLscan_active'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['tipcal_active'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['gaincal_active'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['noisecal_active'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['noisediode_ok_kband'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['noisediode_ok_vband'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['Tstab_ok_kband'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['Tstab_ok_vband'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['recent_powerfailure'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['Tstab_ok_amb'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int
    data['noisediode_on'] = np.ones(data['n_meas'], dtype=np.int8) * missing_int

    # read measurement info
    for n in range(data['n_meas']):
        data['time'][n] = interpret_time(struct.unpack_from('<i', d, byte_offset)[0])
        byte_offset += 4
        data['alarm'][n] = struct.unpack_from('<B', d, byte_offset)[0]
        byte_offset += 1
        if data['has_coord']:
            data['lon'][n] = interpret_coord(struct.unpack_from('<f', d, byte_offset)[0])
            byte_offset += 4
            data['lat'][n] = interpret_coord(struct.unpack_from('<f', d, byte_offset)[0])
            byte_offset += 4
        if data['has_T']:
            data['T_amb_1'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
            data['T_amb_2'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
            data['T_receiver_kband'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
            data['T_receiver_vband'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
        if data['has_stability']:
            data['Tstab_kband'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
            data['Tstab_vband'][n] = struct.unpack_from('<f', d, byte_offset)[0]
            byte_offset += 4
        if data['has_flashmemoryinfo']:
            data['flashmemory_remaining'][n] = struct.unpack_from('<i', d, byte_offset)[0]
            byte_offset += 4
        if data['has_qualityflag']:
            data['L2_qualityflag'][n] = struct.unpack_from('<i', d, byte_offset)[0]
            # don't interpret L2 qualityflag further. Refer to manual for interpretation
            byte_offset += 4
        if data['has_statusflag']:
            statusflagbits = np.unpackbits(
                np.array(struct.unpack_from('<i', d, byte_offset)).view(np.uint8),
                bitorder='little')
            byte_offset += 4

            # interpret statusflagbits
            data['channel_quality_ok_kband'][n] = statusflagbits[0:n_freq_kband]
            data['channel_quality_ok_vband'][n] = statusflagbits[8:(8 + n_freq_vband)]
            data['rainflag'][n] = statusflagbits[16]
            data['blowerspeed_status'][n] = statusflagbits[17]
            data['BLscan_active'][n] = statusflagbits[18]
            data['tipcal_active'][n] = statusflagbits[19]
            data['gaincal_active'][n] = statusflagbits[20]
            data['noisecal_active'][n] = statusflagbits[21]
            data['noisediode_ok_kband'][n] = statusflagbits[22]
            data['noisediode_ok_vband'][n] = statusflagbits[23]
            Tstabflag_kband = statusflagbits[24] + 2 * statusflagbits[25]
            if Tstabflag_kband > 0:
                data['Tstab_ok_kband'][n] = 1 if Tstabflag_kband == 1 else 0  # 1:ok, 0:insufficient, fillvalue:unknown
            Tstabflag_vband = statusflagbits[26] + 2 * statusflagbits[27]
            if Tstabflag_vband > 0:
                data['Tstab_ok_vband'][n] = 1 if Tstabflag_vband == 1 else 0  # 1:ok, 0:insufficient, fillvalue:unknown
            data['recent_powerfailure'][n] = statusflagbits[28]
            data['Tstab_ok_amb'][n] = np.int(not statusflagbits[29])  # 1:ok, 0:not ok because sensors differ by >0.3 K
            data['noisediode_on'][n] = statusflagbits[30]

    return data


###############################################################################
# Helper functions
# ------------------------------------------------------------------------------

def interpret_time(time_in):
    """translate the time format of RPG files to datetime object"""
    posix_offset = dt.datetime.timestamp(dt.datetime(2001, 1, 1))  # offset between RPG and POSIX time in seconds
    times = [dt.datetime.fromtimestamp(x + posix_offset) for x in time_in]
    return np.array(times)


def interpret_angle(x, version):
    """
    translate the angle encoding from RPG to elevation and azimuth in degrees

    Parameters
    ----------
    x : float
        RPG angle.
    version : int
        version of RPG angle encoding:
        1: sign(ele) * (abs(ele)+1000*azi)
        2: digits 1-5 = elevation*100; digits 6-10 = azimuth*100

    Returns
    -------
    ele : float
        elevation
    azi : float
        azimuth

    """

    if version == 1:
        if x >= 1e6:
            x -= 1e6
            ele_offset = 100
        else:
            ele_offset = 0
        azi = (np.abs(x) // 100) / 10  # assume azi and ele are measured in 0.1 degree steps
        ele = x - np.sign(x) * azi * 1000 + ele_offset
    elif version == 2:
        ele = np.sign(x) * (np.abs(x) // 1e5) / 100
        azi = (np.abs(x) - np.abs(ele) * 1e7) / 100
    else:
        raise ValueError('Known versions for angle encoding are 1 and 2, but received %f' % version)

    return ele, azi


def interpret_coord(x, version=2):
    """
    Translate coordinate encoding from RPG to degrees with decimal digits.

    Parameters
    ----------
    x : float
    version : int
        version of RPG angle encoding:
        1: latitude of lognitude in fomrat (-)DDDMM.mmmm where DDD is degrees,
        MM is minutes and mmmm is the decimal fraction of MM
        2: latitude and longitude already in decimal degrees. function does nothing

    Returns
    -------
    out : float
        latitude or longitude in format decimal degrees.

    """

    if version == 1:
        degabs = np.abs(x) // 100
        minabs = np.abs(x) - degabs * 100
        return np.sign(x) * (degabs + minabs / 60)
    return x


def scan_starttime_to_time(starttime, n_angles, inttime=40, caltime=40, idletime=1.4):
    """
    RPG scan files only have one timestamp per scan. This function returns the
    approximative timestamp for the observations at each angle

    Parameters
    ----------
    scan_starttime : datetime.datetime
        the single timestamp saved with the angle scan. Assumed as the start 
        time of the scan
    n_angles : int
        number of angles per scan.
    inttime : int, optional
        integration time at each angle in seconds. The default is 40.
    caltime : int, optional
        integration time for the internal calibration before each scan [s]. 
        The default is 40.
    idletime : float, optional
        time duration for moving the pointing to the repective scan poisiton. 
        The default is 1.4.

    Returns
    -------
    time : np.array of datetime.datetime objects
        list of timestamps for each observed angle

    """

    time = np.empty(n_angles, dtype=np.dtype(dt.datetime))
    time[0] = starttime + dt.timedelta(seconds=caltime)
    for n in range(1, n_angles):
        time[n] = time[n - 1] + dt.timedelta(seconds=caltime + idletime)

    return time


###############################################################################
# main
# ------------------------------------------------------------------------------


filename = './testdata/rpg/C00-V859_190803'

filename_noext = os.path.splitext(filename)[0]  # make sure that filename has no extension
brt = BRT(filename_noext + '.BRT')
brt = read_brt(filename_noext + '.BRT')
blb = read_blb(filename_noext + '.BLB')
irt = read_irt(filename_noext + '.IRT')
met = read_met(filename_noext + '.MET')
hkd = read_hkd(filename_noext + '.HKD')
