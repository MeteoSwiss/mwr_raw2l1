import datetime
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

    for ind, hd in enumerate(header):
        if simplify_header(hd) == simplify_header(header_time):
            t_raw = data_raw[:, ind]
            break

    return np.array([datetime.datetime.strptime(tt, date_format) for tt in t_raw])


def check_vars(data, mandatory_vars):
    """check that 'mandatory_vars' exist in 'data'"""
    for var in mandatory_vars:
        if var not in data:
            raise MissingVariable("Mandatory variable '{}' was not found in data".format(var))


def check_input_filelist(files):
    if isinstance(files, str):
        raise WrongInputFormat('input needs to be a list of files but got a string')


def simplify_header(str_in):
    """simplify strings to match col headers more robustly. Use on both sides of the '==' operator"""
    return str_in.lower().replace(' ', '').replace('[', '(').replace(']', ')')