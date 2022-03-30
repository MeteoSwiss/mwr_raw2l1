import csv

import numpy as np
from mwr_raw2l1.utils.file_utils import abs_file_path


class Reader(object):
    def __init__(self, filename):  # inputs to lists instead of dicts col_headers > col_header and drop first_line_data
        self.filename = filename
        self.header = dict(col_header=[], cfg_info=[], n_lines=np.nan)
        self.data_raw = []
        self.data = []

    def run(self):
        self.read()
        self.interpret_data()

    def read(self, header_only=False):  # same as radiometrics except delimiter='\t'
        """read the data form csv and fill self.header and self.data_raw"""
        with open(self.filename, newline='') as f:  # need to keep file open until all lines are consumed
            csv_lines = csv.reader(f, delimiter='\t')
            self._read_header(csv_lines)
            if not header_only:
                self._read_data(csv_lines)
                self.data_raw_to_np()

    def _read_header(self, csv_lines):
        for n, line in enumerate(csv_lines):
            line = [ll.strip() for ll in line]
            if not line:
                continue
            if line[0].lower() == 'data time':
                self.header['col_header'] = line
                self.header['n_lines'] = n
                break
            self.header['cfg_info'].append(line)

    def _read_data(self, csv_lines):
        for line in csv_lines:
            self.data_raw.append(line)

    def data_raw_to_np(self):  # trivial for attex
        self.data_raw = np.array(self.data_raw)

    def interpret_data(self):
        pass


if __name__ == '__main__':
    rd = Reader(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    pass
