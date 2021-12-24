import csv

from mwr_raw2l1.utils.file_utils import abs_file_path


def read_header(filename):
    """CARE: This procedure will not work for files as lv0 files which don't have data headers on top of file"""
    with open(filename, newline='') as f:
        linereader = csv.reader(f, delimiter=',')
        ct = 0
        headerlines = []
        for line in linereader:
            if line[0] != 'Record':
                break
            headerlines.append(line)
    return headerlines


if __name__ == '__main__':
    hl = read_header(abs_file_path('mwr_raw2l1/data/radiometrics/2021-01-31_00-04-08_lv1.csv'))
    for line in hl:
        print(line)
