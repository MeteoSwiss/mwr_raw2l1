import csv

import numpy as np

from mwr_raw2l1.errors import MissingVariable
from mwr_raw2l1.readers.reader_helpers import get_time
from mwr_raw2l1.utils.file_utils import abs_file_path


class Reader(object):
    def __init__(self, filename):  # inputs to lists instead of dicts col_headers > col_header and drop first_line_data
        self.filename = filename
        self.header = dict(col_header=[], cfg_info=[], n_lines=np.nan)
        self.data_raw = []
        self.data = {}

    def run(self):
        """main method of the class"""
        self.read()
        self.interpret_data()
        del self.data_raw  # after interpret_data() all contents of data_raw have been translated to data

    def read(self, header_only=False):  # same as Radiometrics except delimiter='\t' instead of ','
        """read the data form csv and fill self.header (dictionary) and self.data_raw (:class:`numpy.ndarray`)"""
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

    def data_raw_to_np(self):  # trivial for Attex but keep function for analogy to Radiometrcs
        """in-place replacement for """
        self.data_raw = np.array(self.data_raw)

    def interpret_data(self):
        """fill up self.data using self.data_raw and self.header"""
        time_header = 'data time'
        time_format = '%d/%m/%Y %H:%M:%S'
        temperature_header = 'OutsideTemperature'

        self.data['time'] = get_time(self.data_raw, self.header['col_header'], time_header, time_format)
        self.data['frequency'] = self.get_freq()
        self.data['ele'], cols_tb = self.get_ele()
        self.data['Tb'] = self.data_raw[:, cols_tb]
        col_temperature = self.header['col_header'].index(temperature_header)
        self.data['T'] = self.data_raw[:, col_temperature]

    def get_freq(self):
        """get frequency from header info"""
        for line in self.header['cfg_info']:
            if 'Freq[GHz]' in line:
                return np.array([float(line[0])])
        raise MissingVariable('Frequency not found in {}'.format(self.filename))

    def get_ele(self):
        """get elevations from column headers

        interpret all numeric column headers as elevations. Returned column indices can be used to get corresponding Tb

        Returns:
             ele, column_indices
        """
        ele = []
        columns_ele = []
        for n, hd in enumerate(self.header['col_header']):
            try:
                ele.append(float(hd))
            except ValueError:
                continue
            columns_ele.append(n)
        return np.array(ele), columns_ele


if __name__ == '__main__':
    rd = Reader(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    pass
