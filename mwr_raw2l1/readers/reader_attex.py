import csv
import os

import numpy as np

from mwr_raw2l1.errors import MissingHeader, MissingData, MissingVariable
from mwr_raw2l1.log import logger
from mwr_raw2l1.readers.reader_helpers import check_input_filelist, get_time
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

        if not self.header['col_header']:
            raise MissingHeader('No column header has been found')

    def _read_data(self, csv_lines):
        for line in csv_lines:
            self.data_raw.append(line)

        # remove final line if not printable, e.g. end of file character. (make sure data_raw is not already empty)
        if self.data_raw and not self.data_raw[-1][0].isprintable():
            del self.data_raw[-1]

        if not self.data_raw:
            raise MissingData('Data section in input file is empty')

    def data_raw_to_np(self):  # trivial for Attex but keep function for analogy to Radiometrcs
        """in-place replacement for self.data_raw to a numpy array"""
        self.data_raw = np.array(self.data_raw)

    def interpret_data(self):
        """fill up self.data using self.data_raw and self.header"""
        time_header = 'data time'
        time_format = '%d/%m/%Y %H:%M:%S'
        temperature_header = 'OutsideTemperature'

        self.data['time'] = get_time(self.data_raw, self.header['col_header'], time_header, time_format)
        self.data['frequency'] = self.get_freq()
        self.data['scan_ele'], cols_tb = self.get_ele()
        self.data['Tb'] = self.data_raw[:, cols_tb].astype(float)
        col_temperature = self.header['col_header'].index(temperature_header)
        self.data['T'] = self.data_raw[:, col_temperature].astype(float)

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
        extension = os.path.splitext(file)[-1]
        if extension.lower() == '.tbr':
            reader_inst = Reader(file)
            reader_inst.run()
            all_data.append(reader_inst)
        else:
            logger.warning("Cannot read {} as no reader is specified for files with extension '{}'".format(
                file, extension))

    return all_data


if __name__ == '__main__':
    r1 = read_multiple_files([abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr')])
    rd = Reader(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    pass
