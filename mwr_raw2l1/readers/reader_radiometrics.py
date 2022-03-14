import csv

import numpy as np

from mwr_raw2l1.errors import UnknownRecordType
from mwr_raw2l1.utils.file_utils import abs_file_path

IND_RECORD_TYPE = 2  # third element in line of csv file refers to record type


class reader(object):
    def __init__(self, filename):
        self.filename = filename
        self.header = dict(col_headers={}, cfg_info=[], n_lines=np.nan, first_line_data=[])
        self.data = {}

    def run(self):
        self.read()

    def read(self, header_only=False):
        with open(self.filename, newline='') as f:  # need to keep file open until all lines are consumed
            csv_lines = csv.reader(f, delimiter=',')
            self._read_header(csv_lines)
            if not header_only:
                self._read_data(csv_lines)

    def _read_header(self, csv_lines):
        """read the header of the csv data"""

        for n, line in enumerate(csv_lines):
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
        """read data section of the csv data and relate to header. Assume reader has been read before so that"""

        # init corresponding list of lines
        for rec_type_nb in self.header['col_headers'].keys():
            self.data[rec_type_nb] = []

        # continue iterating over csv_lines assuming header has already been read (incl. first data line)
        self.sort_data_line(self.header['first_line_data'])
        for n, line in enumerate(csv_lines):
            self.sort_data_line(line)

    def sort_data_line(self, line):
        """attribute a csv line of the data section to the correct header reference"""
        rec_type_nb = int(line[IND_RECORD_TYPE])
        # corresponding header rec type nb is always 1 lower e.g. 50 is header for data with nb 51
        rec_type_nb_header = (rec_type_nb - 1)
        if rec_type_nb_header in self.data:
            self.data[rec_type_nb_header].append(line)
        else:
            raise UnknownRecordType('Found data with record type number {} but no header with record type number {}'
                                    'which was assumed to correspond'.fromat(rec_type_nb, rec_type_nb_header))


if __name__ == '__main__':
    rd = reader(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.read()
    pass
