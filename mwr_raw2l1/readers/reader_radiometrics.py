import csv

import numpy as np

from mwr_raw2l1.errors import UnknownRecordType
from mwr_raw2l1.readers.reader_radiometrics_helpers import check_vars, get_data
from mwr_raw2l1.utils.file_utils import abs_file_path

IND_RECORD_TYPE = 2  # third element in line of csv file refers to record type


class Reader(object):
    def __init__(self, filename):
        self.filename = filename
        self.header = dict(col_headers={}, cfg_info=[], n_lines=np.nan, first_line_data=[])
        self.data_raw = {}
        self.data = {}

    def run(self):
        self.read()
        self.interpret_data()

    def read(self, header_only=False):
        """read the data form csv and fill self.header and self.data_raw"""
        with open(self.filename, newline='') as f:  # need to keep file open until all lines are consumed
            csv_lines = csv.reader(f, delimiter=',')
            self._read_header(csv_lines)
            if not header_only:
                self._read_data(csv_lines)
                self.data_raw_to_np()

    def _read_header(self, csv_lines):
        """read the header of the csv data"""

        for n, line in enumerate(csv_lines):
            line = [ll.strip() for ll in line]  # ugly csv formatting leaves white spaces with headers
            rec_type_nb = int(line[IND_RECORD_TYPE])
            if (rec_type_nb % 10) == 0:  # 10-divisible: different column headers (expected as single line)
                self.header['col_headers'][rec_type_nb] = line
            elif rec_type_nb == 99:  # 99: cp of config (can contain multiple lines)
                self.header['cfg_info'].append(line)
            else:  # header seems consumed as none of the known record type numbers for header info follows
                self.header['first_line_data'] = line
                self.header['n_lines'] = n
                break

    def _read_data(self, csv_lines):
        """read data section of the csv data and relate to header. Assume header has been read before"""

        # init corresponding list of lines
        for rec_type_nb in self.header['col_headers'].keys():
            self.data_raw[rec_type_nb] = []

        # continue iterating over csv_lines assuming header has already been read (incl. first data line)
        self.sort_data_line(self.header['first_line_data'])
        for n, line in enumerate(csv_lines):
            self.sort_data_line(line)

    def sort_data_line(self, line):
        """attribute a csv line of the data section to the correct header reference"""
        rec_type_nb = int(line[IND_RECORD_TYPE])
        # corresponding header rec type nb is always 1 lower e.g. 50 is header for data with nb 51
        rec_type_nb_header = (rec_type_nb - 1)
        if rec_type_nb_header in self.data_raw:
            self.data_raw[rec_type_nb_header].append(line)
        else:
            raise UnknownRecordType('Found data with record type number {} but no header with record type number {} '
                                    'which was assumed to correspond'.format(rec_type_nb, rec_type_nb_header))

    def data_raw_to_np(self):
        """transform list of lists in data_raw to numpy array and remove entries without data"""
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

    def interpret_data(self):
        """interpret the data in 'data_raw' and feed to 'data'"""
        self.interpret_mwr()
        self.interpret_aux()

    def interpret_mwr(self):
        """interpret microwave radiometer data"""
        rec_type_nb = 50
        mandatory_vars = ['time', 'frequency', 'Tb', 'azi', 'ele', 'quality']

        data = get_data(self.data_raw[rec_type_nb], self.header['col_headers'][rec_type_nb])
        check_vars(data, mandatory_vars)
        self.data['mwr'] = data

    def interpret_aux(self):
        """interpret auxiliary data, i.e. infrared brightness temperatures and meteo observations"""
        rec_type_nb = 40
        mandatory_vars = ['time', 'T', 'RH', 'IRT', 'rainflag', 'quality']

        data = get_data(self.data_raw[rec_type_nb], self.header['col_headers'][rec_type_nb], no_mwr=True)
        check_vars(data, mandatory_vars)
        self.data['aux'] = data


if __name__ == '__main__':
    rd = Reader(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    pass
