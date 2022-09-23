import datetime as dt

import numpy as np

from mwr_raw2l1.errors import MissingVariable, WrongInputFormat


def get_time(data_raw, header, header_time, date_format):
    """extract time from data_raw using header

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
        header_time: the pattern for matching the time variable in the header
        date_format: format how the date is encoded in the string. Used by :class:`datetime.datetime`
    Returns:
        a :class:`numpy.ndarray` of :class:`datetime.datetime` objects
    """

    ind = get_column_ind(header, header_time)
    return np.array([dt.datetime.strptime(tt, date_format) for tt in data_raw[:, ind]])


def get_column_ind(header, column_title):
    """get the zero-based column index corresponding to the column title

    Args:
        header: list of all column headers
        column_title: column title to search for in the header
    Returns:
        the index of the column corresponding to column_title
    """
    for ind, hd in enumerate(header):
        if simplify_header(hd) == simplify_header(column_title):
            return ind


def check_vars(data, mandatory_vars):
    """check that 'mandatory_vars' exist in 'data'"""
    for var in mandatory_vars:
        if var not in data:
            raise MissingVariable("Mandatory variable '{}' was not found in data".format(var))


def simplify_header(str_in):
    """simplify strings to match col headers more robustly. Use on both sides of the '==' operator"""
    return str_in.lower().replace(' ', '').replace('[', '(').replace(']', ')')


def check_input_filelist(files):
    """check that input files are given as a list and not as a single string"""
    if isinstance(files, str):
        raise WrongInputFormat('input needs to be a list of files but got a string')
