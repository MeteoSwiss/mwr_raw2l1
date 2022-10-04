import csv
import os

import numpy as np

from mwr_raw2l1.errors import EmptyLineError, MissingData, MissingHeader, UnknownRecordType
from mwr_raw2l1.log import logger
from mwr_raw2l1.readers.reader_helpers import check_input_filelist, check_vars
from mwr_raw2l1.readers.reader_radiometrics_helpers import get_data, get_record_type
from mwr_raw2l1.utils.file_utils import abs_file_path


class Reader(object):
    def __init__(self, filename):
        self.filename = filename
        self.header = dict(col_headers={}, cfg_info=[], n_lines=np.nan, first_line_data=[])
        self.data_raw = {}
        self.data = {}

    def run(self):
        """main method of the class"""
        self.read()
        self.interpret_data()
        del self.data_raw  # after interpret_data() all contents of data_raw have been translated to data

    def read(self, header_only=False):
        """read the data form csv and fill self.header and self.data_raw"""
        with open(self.filename, newline='') as f:  # need to keep file open until all lines are consumed
            csv_lines = csv.reader(f, delimiter=',')
            self._read_header(csv_lines)
            if not header_only:
                self._read_data(csv_lines)
                self.data_raw_to_np()

    def interpret_data(self):
        """interpret the data in self.data_raw and feed to self.data"""
        self.interpret_mwr()
        self.interpret_aux()

    def interpret_mwr(self):
        """interpret microwave radiometer data"""
        rec_type_nb = 50  # record type number for header: 50; for data: 51.
        mandatory_vars = ['record_nb', 'time', 'frequency', 'Tb', 'azi', 'ele', 'quality']

        data = get_data(self.data_raw[rec_type_nb], self.header['col_headers'][rec_type_nb])
        check_vars(data, mandatory_vars)
        self.data['mwr'] = data

    def interpret_aux(self):
        """interpret auxiliary data, i.e. infrared brightness temperatures and meteo observations"""
        rec_type_nb = 40
        mandatory_vars = ['record_nb', 'time', 'T', 'RH', 'IRT', 'rainflag', 'quality']

        data = get_data(self.data_raw[rec_type_nb], self.header['col_headers'][rec_type_nb], no_mwr=True)
        check_vars(data, mandatory_vars)
        self.data['aux'] = data

    def _read_header(self, csv_lines):
        """read the header of the csv data (all 10-divisible record type numbers and 99)"""

        while True:
            try:
                line = next(csv_lines)
            except StopIteration:
                # usual way of leaving loop is through break when record_type_nb does not correspond to header anymore
                if csv_lines.line_num == 0:
                    raise MissingData('Input file is empty')
                else:
                    raise MissingData('Data section in input file is empty')

            line = [ll.strip() for ll in line]  # strip as ugly csv formatting leaves white spaces with headers
            try:
                rec_type_nb = get_record_type(line)
            except EmptyLineError:
                continue  # ignore empty lines and continue with next

            if (rec_type_nb % 10) == 0:  # 10-divisible: different column headers (expected as single line)
                self.header['col_headers'][rec_type_nb] = line
            elif rec_type_nb == 99:  # 99: cp of config (can contain multiple lines)
                self.header['cfg_info'].append(line)
            else:  # header seems consumed as none of the known record type numbers for header info follows
                self.header['first_line_data'] = line
                self.header['n_lines'] = csv_lines.line_num - 1
                break

        if not self.header['col_headers']:
            raise MissingHeader('No column header has been found')

    def _read_data(self, csv_lines):
        """read data section of the csv data and relate to header. Assume header has been read before"""

        # init corresponding list of lines
        for rec_type_nb in self.header['col_headers'].keys():
            self.data_raw[rec_type_nb] = []

        # iterate over csv_lines assuming header has already been read (incl. first data line)
        try:
            self.sort_data_line(self.header['first_line_data'])
        except UnknownRecordType:
            logger.warning('first line after header is ignored as it does not correspond to expected format of data')
        except EmptyLineError:
            pass  # silently ignore empty line after header

        for line in csv_lines:
            try:
                self.sort_data_line(line)
            except EmptyLineError:
                continue  # ignore empty lines and continue with next

    def sort_data_line(self, line):
        """attribute a csv line of the data section to the correct header reference"""
        rec_type_nb = get_record_type(line)
        # corresponding header rec type nb is always 1 lower e.g. 50 is header for data with nb 51
        rec_type_nb_header = (rec_type_nb - 1)
        if rec_type_nb_header in self.data_raw:
            self.data_raw[rec_type_nb_header].append(line)
        else:
            raise UnknownRecordType('Found data with record type number {} but no header with record type number {} '
                                    'which was assumed to correspond'.format(rec_type_nb, rec_type_nb_header))

    def data_raw_to_np(self):
        """transform data_raw to a dictionary with values of :class:`numpy.ndarray` and remove entries without data"""
        empty_rec = []
        for rec_type, dat in self.data_raw.items():
            if not dat:
                empty_rec.append(rec_type)
                continue
            x = np.array(dat)
            x[x == ''] = np.nan
            self.data_raw[rec_type] = x
        for rec_type in empty_rec:
            del self.data_raw[rec_type]


def read_multiple_files(files):
    """read multiple L1-related files and return list of executed read-in class instances

    Args:
        files: list of files to read in
    Returns:
        list of instances of executed read-in classes of :class:`Reader`.
    """

    check_input_filelist(files)
    all_data = []
    for file in files:
        suffix = os.path.splitext(file)[0].split('_')[-1]
        if suffix.lower() == 'lv1':
            reader_inst = Reader(file)
            reader_inst.run()
            all_data.append(reader_inst)
        else:
            logger.warning("Cannot read {} as no reader is specified for files with suffix '{}'".format(file, suffix))

    return all_data


if __name__ == '__main__':
    rd = Reader(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    pass
