from itertools import groupby

import numpy as np

from mwr_raw2l1.errors import WrongInputFormat


def is_var_in_data(data, var):
    """Return False if 'var' is not in data or if data['var'] is all NaN, otherwise True"""
    return var in data and not all(np.isnan(data[var]))


def is_full_var_in_data(data, var):
    """Return False if 'var' is not in data or if any value of data['var'] is NaN, otherwise True"""
    return var in data and not any(np.isnan(data[var]))


def channels2receiver(freq, band_limits=None, base=1):
    """attribute receiver numbers (1, 2, ...) to frequency channels according to frequency bands

    Args:
        freq: frequency vector in GHz
        band_limits (optional): limit frequencies (in GHz) between different receivers. Need max(band_limits)<max(freq)
        base (optional): indexing base for attributing receiver numbers.
            base=1 returns numbers 1, 2, ...; base=0 returns 0, 1, ...; Defaults to 1.
    """
    if band_limits is None:
        band_limits = [0, 1, 2, 4, 8, 12, 40, 75, 110, 300, np.inf]

    # attribute channels to different bands
    rec_nb_tmp = np.full(np.shape(freq), np.nan)
    for ind, f in enumerate(freq):
        for n, lim in enumerate(band_limits):
            if f < lim:
                rec_nb_tmp[ind] = n
                break

    # count for receivers only if existing
    _, rec_nb_0 = np.unique(rec_nb_tmp, return_inverse=True)  # zero-based receiver number

    return rec_nb_0 + base


def get_receiver_vars(varnames, search_pattern='receiver', sep='_'):
    """find receiver-specific variable names

    Assumes last part separated by 'sep' must be an integer and second-last part must match 'search_pattern'

    Args:
        varnames: iterable of strings representing variable names
        search_pattern: string characterising a receiver-specific variable in second-last block
        sep: separator between filename parts
    Returns:
        a dictionary where the keys correspond to the base variable name and the values contain a list of all receiver-
        specific variables contributing to this base variable name
    """
    variables = []
    for var in sorted(varnames):
        var_parts = var.split(sep)
        if len(var_parts) > 2 and var_parts[-2] == search_pattern:
            try:
                int(var_parts[-1])  # don't need to keep receiver number as input sorted anyway
            except ValueError:   # last part must be numeric, otherwise not what we search for
                continue
            variables.append(var)

    # define helper function rec-splitter and use it in groupby to generate ouptut
    def rec_splitter(x):
        return split_receiver(x, sep=sep)
    var_groups = groupby(variables, key=rec_splitter)
    return {base_name: list(var_group) for base_name, var_group in var_groups}


def split_receiver(varname, sep='_'):
    """split off receiver part (i.e. part after second-last sep) from varname"""
    try:
        basename_parts = varname.split(sep)[:-2]
    except IndexError:
        raise WrongInputFormat("input argument 'varname' does not seem to have a receiver suffix. "
                               "Expected sth like 'xxx_receiver_1'")
    return sep.join(basename_parts)


if __name__ == '__main__':
    out = channels2receiver([22.2, 23.0, 23.8, 25.4, 26.2, 27.8, 31.4, 51.3, 52.3, 53.9, 54.9, 56.7, 57.3, 58.0, 183])

    vars = get_receiver_vars(['T_amb_receiver_1', 'receiver_nb', 'T', 'T_amb_receiver_2'])
