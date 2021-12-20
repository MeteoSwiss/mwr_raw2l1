import struct

import numpy as np

from mwr_raw2l1.errors import FileTooLong, FileTooShort, TimeInputMissing, TimerefError, UnknownFileType
from mwr_raw2l1.log import logger
from mwr_raw2l1.readers.reader_rpg_helpers import interpret_angle, interpret_coord, interpret_time
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
}


class BaseReader(object):
    def __init__(self, filename, accept_localtime=False):
        self.filename = filename
        self.data = {}
        self.byte_offset = 0  # counter for consumed bytes, increased by each method
        self.filecode = None
        self.filestruct = None

        # TODO: externalise all this below into a run method for better style
        self.data_bin = get_binary(self.filename)
        self.read()  # fills self.data
        self.check_data(accept_localtime)
        del self.data_bin  # after read() all contents of data_bin have been interpreted to data
        del self.byte_offset  # after read() has checked that all data have been read, this quantity is useless

    def read(self):
        # sequence must be preserved as self.byte_offset is increased by each method, hence they are all semi-private
        self._read_filecode()
        self.interpret_filecode()
        self._read_header()
        self.interpret_header()
        self._read_meas()
        self.interpret_raw_data()
        if self.byte_offset < len(self.data_bin):
            raise FileTooLong('Not all bytes consumed. Interpreted {} bytes during read-in but {} contains {}'.format(
                self.byte_offset, self.filename, len(self.data_bin)))

    def decode_binary(self, encoding_pattern, byte_order=BYTE_ORDER):
        """"
        decode next variables from binary stream and write to dict self.data + augment self.byte_offset
          - encoding_pattern: a list of tuples or lists containing the individual variable description
                              e.g. #TODO give an example of encoding pattern here
        """
        for enc in encoding_pattern:
            full_type = byte_order + np.prod(enc['shape']) * enc['type']
            out = struct.unpack_from(full_type, self.data_bin, self.byte_offset)
            self.byte_offset += struct.calcsize(full_type)  # multiplication with shape already done for full type

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
        bytes_per_var = np.array([struct.calcsize(ep['type']) * np.prod(ep['shape']) for ep in encoding_pattern])

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
        # transform frequency and wavelength to 1D-numpy array for later import to xarray in Measurement classq
        for var in ['frequency', 'wavelength', 'scan_ele']:
            if var in self.data.keys():
                self.data[var] = np.array(self.data[var]).ravel()

    def interpret_raw_data(self):
        try:  # assume data-dict in all subclasses contains time
            self.data['time'] = interpret_time(self.data['time_raw'])
        except KeyError as err:
            raise TimeInputMissing('Did not find {} in read-in data from file {}'.format(err, self.filename))
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
