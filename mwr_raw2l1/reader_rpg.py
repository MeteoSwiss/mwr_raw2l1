"""
reader for RPG HATPRO, TEMPRO or HUMPRO binary files
"""
import os
import struct

import numpy as np

from mwr_raw2l1.errors import (FileTooShort, TimerefError, UnknownFileType,
                               WrongFileType, WrongNumberOfChannels)
from mwr_raw2l1.legacy_reader_rpg import (read_blb, read_brt, read_hkd,
                                          read_irt, read_met)
from mwr_raw2l1.log import logger
from mwr_raw2l1.reader_rpg_helpers import (interpret_angle, interpret_coord,
                                           interpret_hkd_contents_code,
                                           interpret_statusflag,
                                           interpret_time,
                                           scan_starttime_to_time)
from mwr_raw2l1.utils.file_utils import get_binary

BYTE_ORDER = '<'  # byte order in all RPG files assumed little-endian  #TODO: ask Harald whether this is true (PC/Unix)

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
}  # INFO: Volker: different dict structures are ok here as long as they don't cause if clauses in code

N_FREQ_DEFAULT = 14    # TODO: check how RPG deals with files from TEMPRO or HUMPRO how would have different n_freq. Other filecodes? Could also get frequency info from BRT files but ugly dependency.


###############################################################################
# readers for different RPG files
# ------------------------------------------------------------------------------
class BaseReader(object):
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
        self._read_filecode()
        self.interpret_filecode()
        self._read_header()
        self.interpret_header()
        self._read_meas()
        self.interpret_raw_data()

    def decode_binary(self, encoding_pattern, byte_order=BYTE_ORDER):
        """"
        decode next variables from binary stream and write to dict self.data + augment self.byte_offset
          - encoding_pattern: a list of tuples or lists containing the individual variable description
                              e.g. #TODO give an example of encoding pattern here
        """
        for enc in encoding_pattern:
            full_type = byte_order + np.prod(enc['shape']) * enc['type']
            out = struct.unpack_from(full_type, self.data_bin, self.byte_offset)
            self.byte_offset += enc['bytes']

            if len(out) == 1:  # extract from tuple if it has only one element, otherwise return tuple
                self.data[enc['name']] = out[0]
            else:
                self.data[enc['name']] = out

    def decode_binary_np(self, encoding_pattern, n_entries, byte_order=BYTE_ORDER):
        """
        decode bunch of binary stream via 2d numpy array to write to dict self.data + augment self.byte_offset
          - encoding_pattern: a list of tuples or lists containing the individual variable description FOR ONE TIME STEP
                              e.g. #TODO give an example of encoding pattern here
        """
        dtype_np = np.dtype([(ep['name'], byte_order+ep['type'], ep['shape']) for ep in encoding_pattern])
        names = [ep['name'] for ep in encoding_pattern]
        bytes_per_var = np.array([ep['bytes'] for ep in encoding_pattern])

        byte_offset_start = self.byte_offset
        n_bytes = bytes_per_var.sum() * n_entries
        self.byte_offset += n_bytes
        if len(self.data_bin) < self.byte_offset:
            err_msg = 'number of bytes in file {} does not match the one inferred from n_meas'.format(self.filename)
            logger.error(err_msg)
            raise FileTooShort(err_msg)

        arr = np.frombuffer(self.data_bin[byte_offset_start: self.byte_offset], dtype=dtype_np)
        for idx, name in enumerate(names):
            if encoding_pattern[idx]['shape'] == (1,):  # variables which only have a time dimension shall not be 2d
                self.data[name] = arr[name].flatten()
            else:
                self.data[name] = arr[name]

    def interpret_filecode(self):
        try:
            self.filestruct = FILETYPE_CONFS[self.filecode]
        except KeyError:
            raise UnknownFileType('reader not specified for files with filecode {:d} as used in {:s}'.format(
                                  self.filecode, self.filename))

    def interpret_header(self):
        pass

    def interpret_raw_data(self):
        self.data['time'] = interpret_time(self.data['time_raw'])  # assume data-dict in all subclasses contains time
        if 'pointing_raw' in self.data.keys():
            self.data['ele'], self.data['azi'] = interpret_angle(self.data['pointing_raw'], self.filestruct['anglever'])
        for coord in ('lon_raw', 'lat_raw'):
            if coord in self.data.keys():
                self.data[coord[0:3]] = interpret_coord(self.data[coord])

    def check_data(self, accept_localtime):
        """general checks for the consistency of the data which can be applied to all file type readers"""
        if not accept_localtime and self.data['timeref'] == 0:
            raise TimerefError('Time encoded in local time but UTC required by "accept_localtime"')

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


class BRT(BaseReader):
    def interpret_filecode(self):
        super(BRT, self).interpret_filecode()

        # check if filecode corresponds to a BRT file
        if self.filestruct['type'] != 'brt':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for BRT'.format(
                                self.filestruct['type']))

    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_meas', type='i', shape=(1,), bytes=4),  # TODO: Ask Volker about calcsize ==> would be good to use
            dict(name='timeref', type='i', shape=(1,), bytes=4),  # TODO: write more compact with list comprehension just looping over names (rest stays the same) (Volkers suggestion). But could also argue that want to keep same structure for all. Think about
            dict(name='n_freq', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        n_freq = self.data['n_freq']
        encodings_bin_var = [
            dict(name='frequency', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_min', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_max', type='f', shape=(n_freq,), bytes=n_freq * 4)]
        self.decode_binary(encodings_bin_var)

    def _read_meas(self):
        """read actual measurements. Filecode and Header needs to be read before as info is needed for decoding"""
        n_freq = self.data['n_freq']
        encodings_bin = (
            dict(name='time_raw', type='i', shape=(1,), bytes=4),
            dict(name='rainflag', type='B', shape=(1,), bytes=1),
            dict(name='Tb', type='f', shape=(n_freq,), bytes=n_freq*4),
            dict(name='pointing_raw', type=self.filestruct['formatchar_angle'], shape=(1,), bytes=4))
        self.decode_binary_np(encodings_bin, self.data['n_meas'])


class BLB(BaseReader):
    def __init__(self, filename, accept_localtime=False):
        self.header_reader = None
        super(BLB, self).__init__(filename, accept_localtime)

    def interpret_filecode(self):
        super(BLB, self).interpret_filecode()

        # check if filecode corresponds to a BLB file
        if self.filestruct['type'] != 'blb':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for BLB'.format(
                                self.filestruct['type']))

        self.header_reader = getattr(self, '_read_header_{:d}'.format(self.filestruct['structver']))

    def _read_header(self):
        self.header_reader()

    def _read_header_1(self):
        """Function for reading header for files with structver 1 (n_freq first assumed and read only afterwards)"""
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_scans', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        self.data['n_freq'] = N_FREQ_DEFAULT  # need assumption as number of channels is encoded after used for read
        n_freq = self.data['n_freq']
        encodings_bin_var_1 = [
            dict(name='Tb_min', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_max', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='timeref', type='i', shape=(1,), bytes=4),
            dict(name='n_freq_file', type='i', shape=(1,), bytes=4),
            dict(name='frequency', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='n_ele', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin_var_1)

        # quantities with length dependent on number of elevations in scan (n_ele) only possible after n_ele is read
        n_ele = self.data['n_ele']
        encodings_bin_var_2 = [
            dict(name='scan_ele', type='f', shape=(n_ele,), bytes=n_ele * 4)]
        self.decode_binary(encodings_bin_var_2)

    def _read_header_2(self):
        """Function for reading header for files with structver 2 (no assumption on n_freq needed"""
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_scans', type='i', shape=(1,), bytes=4),
            dict(name='n_freq', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        n_freq = self.data['n_freq']
        encodings_bin_var_1 = [
            dict(name='Tb_min', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='Tb_max', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='timeref', type='i', shape=(1,), bytes=4),
            dict(name='frequency', type='f', shape=(n_freq,), bytes=n_freq * 4),
            dict(name='n_ele', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin_var_1)

        # quantities with length dependent on number of elevations in scan (n_ele) only possible after n_ele is read
        n_ele = self.data['n_ele']
        encodings_bin_var_2 = [
            dict(name='scan_ele', type='f', shape=(n_ele,), bytes=n_ele * 4)]
        self.decode_binary(encodings_bin_var_2)

    def interpret_header(self):
        super(BLB, self).interpret_header()
        self.data['n_meas'] = self.data['n_scans'] * self.data['n_ele']

        # check if correct number of channels was assumed for reading in structver 1 file
        if 'n_freq_file' in self.data.keys():
            if self.data['n_freq_file'] != self.data['n_freq']:
                raise WrongNumberOfChannels(
                    'assumed number of channels ({}) for reading this BLB file seems wrong'.format(self.data['n_freq']))

    def _read_meas(self):
        pass  # TODO: implement meas reader for BLB class. harder as 3 dimensional (time, freq, ele)
        n_ele = self.data['n_ele']
        n_freq = self.data['n_freq']
        encodings_bin = (
            dict(name='time_raw', type='i', shape=(1,), bytes=4),  # scan starttime here, will be transformed to series
            dict(name='scanflag', type='B', shape=(1,), bytes=1),
            dict(name='scanobs', type='f', shape=(n_freq, n_ele+1), bytes=n_freq*(n_ele+1)*4))  # Tb on n_ele + T (stored at n_ele+1)
        self.decode_binary_np(encodings_bin, self.data['n_scans'])

    def interpret_raw_data(self):
        super(BLB, self).interpret_raw_data()
        self.interpret_scanobs()
        self.interpret_scanflag()

        # transform single vector of elevations to time series of elevations
        self.data['ele'] = np.tile(self.data['scan_ele'], self.data['n_scans'])

        # TODO: ask Volker what functions shall be methods of BLB and which shall go to reader_rpg_helper

    def interpret_scanobs(self):
        """transform scanobs 3D array to time series of spectra and temperature"""

        # extract ambient temperature (ambient temperature equal for each frequency, one per scan)
        self.data['T_per_scan'] = self.data['scanobs'][:, 0, -1]

        # extract spectra of brightness temperatures for each ele in dimension (time, freq, ele)
        self.data['Tb_scan'] = self.data['scanobs'][:, :, :-1]

    def interpret_scanflag(self):
        pass  # TODO: implement scanflag interpreter

    def scan_to_timeseries(self):
        """transform scans to time series of spectra and temperatures"""
        # TODO find a place where this function should go (maybe reader_rpg_helpers and call after read in also hkd)
        n_freq = self.data['n_freq']
        n_ele = self.data['n_ele']
        n_scans = self.data['n_scans']

        tb_tmp = self.data['Tb_scan'].swapaxes(0, 1)  # swap dim to (freq, time, ele)
        self.data['Tb'] = tb_tmp.reshape(n_freq, n_scans*n_ele, order='C').transpose()

        self.data['T'] = self.data['T_per_scan'].repeat(n_ele)  # repeat to have one T value for each new time

        # time is encoded as start time of scan (same time for all elevations). need to transform to time series
        # self.data['time'] = scan_starttime_to_time(self.data['time'], self.data['n_ele'])  # TODO: vectorise scan starttime_to_time (and write test)


class IRT(BaseReader):
    def interpret_filecode(self):
        super(IRT, self).interpret_filecode()

        # check if filecode corresponds to a IRT file
        if self.filestruct['type'] != 'irt':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for IRT'.format(
                                self.filestruct['type']))

    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_meas', type='i', shape=(1,), bytes=4),
            dict(name='IRT_min', type='f', shape=(1,), bytes=4),
            dict(name='IRT_max', type='f', shape=(1,), bytes=4),
            dict(name='timeref', type='i', shape=(1,), bytes=4)]  # define as list to be able to append. TODO: Ask Volker whether it is ok to have list here but tuple in BRT. Or should encodings in BRT also be declared as list, although they will not be changed
        if self.filestruct['structver'] >= 2:
            encodings_bin_fix.append(
                dict(name='n_wavelengths', type='i', shape=(1,), bytes=4))
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_wavelenghts) only possible after read
        n_wl = self.data['n_wavelengths']
        encodings_bin_var = [
            dict(name='wavelength', type='f', shape=(n_wl,), bytes=n_wl*4)]
        self.decode_binary(encodings_bin_var)

        # complete missing input for structver == 1
        if self.filestruct['structver'] == 1:
            self.data['n_wavelengths'] = 1
            self.data['wavelength'] = np.nan

    def _read_meas(self):
        n_wl = self.data['n_wavelengths']
        encodings_bin = [
            dict(name='time_raw', type='i', shape=(1,), bytes=4),
            dict(name='rainflag', type='B', shape=(1,), bytes=1),
            dict(name='IRT', type='f', shape=(n_wl,), bytes=n_wl*4)]
        if self.filestruct['structver'] >= 2:
            encodings_bin.append(
                dict(name='pointing_raw', type=self.filestruct['formatchar_angle'], shape=(1,), bytes=4))

        self.decode_binary_np(encodings_bin, self.data['n_meas'])


class MET(BaseReader):
    def interpret_filecode(self):
        super(MET, self).interpret_filecode()

        # check if filecode corresponds to a MET file
        if self.filestruct['type'] != 'met':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for MET'.format(
                                self.filestruct['type']))

    pass  # TODO: implement MET class. For structver >=2 has bit encoding presence of different sensors. Similar to HKD


class HKD(BaseReader):
    def interpret_filecode(self):
        super(HKD, self).interpret_filecode()

        # check if filecode corresponds to a HKD file
        if self.filestruct['type'] != 'hkd':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for HKD'.format(
                                self.filestruct['type']))

    def _read_header(self):
        encodings_bin = [
            dict(name='n_meas', type='i', shape=(1,), bytes=4),
            dict(name='timeref', type='i', shape=(1,), bytes=4),
            dict(name='hkd_contents_code', type='i', shape=(1,), bytes=4)]
        self.decode_binary(encodings_bin)

        file_contents = interpret_hkd_contents_code(self.data['hkd_contents_code'], bit_order=BYTE_ORDER)
        self.data.update(file_contents)  # add variables 'has_...' used below to the data dictionary

    def _read_meas(self):
        encodings_bin = [
            dict(name='time_raw', type='i', shape=(1,), bytes=4),
            dict(name='alarm', type='B', shape=(1,), bytes=1)]
        if self.data['has_coord']:
            encodings_bin.append(dict(name='lon_raw', type='f', shape=(1,), bytes=4))
            encodings_bin.append(dict(name='lat_raw', type='f', shape=(1,), bytes=4))
        if self.data['has_T']:
            encodings_bin.append(dict(name='T_amb_1', type='f', shape=(1,), bytes=4))
            encodings_bin.append(dict(name='T_amb_2', type='f', shape=(1,), bytes=4))
            encodings_bin.append(dict(name='T_receiver_kband', type='f', shape=(1,), bytes=4))
            encodings_bin.append(dict(name='T_receiver_vband', type='f', shape=(1,), bytes=4))  # TODO: Ask Volker if/how I could use inheritance for another instrument which has no V-Band ==> in Funktion auslagern. Eine macht was, andere nichts
        if self.data['has_stability']:
            encodings_bin.append(dict(name='Tstab_kband', type='f', shape=(1,), bytes=4))
            encodings_bin.append(dict(name='Tstab_vband', type='f', shape=(1,), bytes=4))
        if self.data['has_flashmemoryinfo']:
            encodings_bin.append(dict(name='flashmemory_remaining', type='i', shape=(1,), bytes=4))
        if self.data['has_qualityflag']:
            encodings_bin.append(dict(name='L2_qualityflag', type='i', shape=(1,), bytes=4))
        if self.data['has_statusflag']:
            encodings_bin.append(dict(name='statusflag', type='i', shape=(1,), bytes=4))

        self.decode_binary_np(encodings_bin, self.data['n_meas'])

    def interpret_raw_data(self):
        super(HKD, self).interpret_raw_data()
        self.data.update(interpret_statusflag(self.data['statusflag']))


# TODO: Consider transforming to SI units. IRT/IRT_min/IRT_max -> K; wavelength -> m; frequency -> Hz. could be done in interpret_raw_data of BaseReader class
###############################################################################
# main
# ------------------------------------------------------------------------------

def main():

    filename = 'data/rpg/C00-V859_190803'

    filename_noext = os.path.splitext(filename)[0]  # make sure that filename has no extension

    brt = BRT(filename_noext + '.BRT')
    blb = BLB(filename_noext + '.BLB')  # TODO: first need to finish reader
    irt = IRT(filename_noext + '.IRT')
    # met = MET(filename_noext + '.MET')
    hkd = HKD(filename_noext + '.HKD')

    # legacy readers
    brt_old = read_brt(filename_noext + '.BRT')
    blb_old = read_blb(filename_noext + '.BLB')
    irt_old = read_irt(filename_noext + '.IRT')
    met_old = read_met(filename_noext + '.MET')
    hkd_old = read_hkd(filename_noext + '.HKD')
    pass


if __name__ == '__main__':
    main()
