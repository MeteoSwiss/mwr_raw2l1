import csv

import numpy as np

from mwr_raw2l1.errors import UnknownRecordType
from mwr_raw2l1.utils.file_utils import abs_file_path

IND_RECORD_TYPE = 2  # third element in line of csv file refers to record type


class reader(object):
    def __init__(self, filename):
        self.filename = filename
        self.header = dict(col_headers={}, cfg_info=[], n_lines=np.nan, first_line_data=[])
        self.data_raw = {}
        self.data = {}

    def run(self):
        self.read()
        self.interpret_data()

    def read(self, header_only=False):
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
            raise UnknownRecordType('Found data with record type number {} but no header with record type number {}'
                                    'which was assumed to correspond'.fromat(rec_type_nb, rec_type_nb_header))

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

        self.data['Tb'], self.data['frequency'] = get_mwr(self.data_raw[50], self.header['col_headers'][50])
        self.extract_data(self.data_raw[50], self.header['col_headers'][50])

    def extract_data(self, data_raw, header):
        # rec type 40 (aux=met+irt)
        # Tamb(K),Rh(%),Pres(mb),Tir(K),Rain,DataQuality
        # rec type 50 (mwr)
        # Az(deg),El(deg),TkBB(K),Ch....,DataQuality
        var2colheader = {'azi': 'Az(deg)', 'ele': 'El(deg)', 'T_amb': 'TkBB(K)',
                         'T': 'Tamb(K)', 'RH': 'Rh(%)', 'p': 'Pres(mb)',
                         'IRT': 'Tir(K)', 'rainflag': 'Rain', 'quality': 'DataQuality'}
        for varname, colhead in var2colheader.items():
            for ind, hd in enumerate(header):
                if simplify_header(hd) == simplify_header(colhead):
                    self.data[varname] = data_raw[:, ind].astype(float)  # TODO: do not directly write to data, only do this for right record types


# to helpers
def simplify_header(str_in):
    """simplify strings to match col headers more robustly. Use on both sides of the '==' operator"""
    return str_in.lower().replace(' ', '').replace('[', '(').replace(']', ')')


def get_mwr(data_raw, header, only_observed_freq=True):
    """extract the microwave radiometer brightness temperatures and frequencies from raw_data

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
        only_observed_freq: if True only frequencies with non-NaN observations are returned. Defaults to True.
    Returns:
        the tuple (brightness_temperature, frequency)
    """

    # find indices of MWR data and their frequency from header
    ind_mwr = []
    freq = []
    for ind, colhead in enumerate(header):
        if 'ch ' == colhead[0:3].lower():
            ind_mwr.append(ind)
            freq.append(float(colhead[3:]))
    frequency = np.array(freq)

    # get brightness temperatures and exclude channels without observations if requested
    # TODO: ask Christine what she thinks about excluding unused channels. channel reporting temporarily NaN possible?
    tb = data_raw[:, ind_mwr].astype(float)
    if only_observed_freq:
        ind_obs = ~np.all(np.isnan(tb), axis=0)
        tb = tb[:, ind_obs]
        frequency = frequency[ind_obs]

    return tb, frequency


if __name__ == '__main__':
    rd = reader(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    pass
