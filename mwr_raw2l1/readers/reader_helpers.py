import datetime as dt

import numpy as np

from mwr_raw2l1.errors import MissingVariable


def get_time(data_raw, header, header_time):
    """extract time from data_raw using header

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
        header_time: the pattern for matching the time variable in the header
    Returns:
        a :class:`numpy.ndarray` of :class:`datetime.datetime` objects
    """

    for ind, hd in enumerate(header):
        if simplify_header(hd) == simplify_header(header_time):
            t_raw = data_raw[:, ind]
            break

    return np.array([interpret_time_str(tt) for tt in t_raw])


def interpret_time_str(time_str):
    """interpret a Radiometrics time strings and return a :class:`datetime.datetime` object"""

    #    (full year           , month        , day          , hour          , minute         , second         )
    tt = ('20' + time_str[6:8], time_str[0:2], time_str[3:5], time_str[9:11], time_str[12:14], time_str[15:17])
    tt_int = [int(x) for x in tt]
    return dt.datetime(*tt_int)  # don't use tzinfo here, otherwise will not be able to convert to datetime64 by xarray


def check_vars(data, mandatory_vars):
    """check that 'mandatory_vars' exist in 'data'"""
    for var in mandatory_vars:
        if var not in data:
            raise MissingVariable("Mandatory variable '{}' was not found in data".format(var))


def simplify_header(str_in):
    """simplify strings to match col headers more robustly. Use on both sides of the '==' operator"""
    return str_in.lower().replace(' ', '').replace('[', '(').replace(']', ')')