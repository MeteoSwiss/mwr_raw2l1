import numpy as np

from mwr_raw2l1.readers.reader_helpers import get_time, simplify_header


def get_data(data_raw, header, no_mwr=False, **kwargs):
    """extract all known data from data_raw using header

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
        no_mwr: indicate whether data_raw contains channels of MWR observations. Defaults to False (contains MWR data).
        **kwargs: keyword arguments passed on to :func:`get_mwr`
    Returns
        a dictionary with variable name as key and :class:`numpy.ndarray` as values
    """
    data = get_simple_vars(data_raw, header)
    data['time'] = get_time(data_raw, header, 'date/time')
    if not no_mwr:
        data['Tb'], data['frequency'] = get_mwr(data_raw, header, **kwargs)
    return data


def get_simple_vars(data_raw, header):
    """extract variables from data_raw according to header, except the MWR brightness temperatures/frequencies and time

    Note: For extracting brightness temperatures and frequencies use :func:`get_mwr`; for time use :func:`get_time`

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
    Returns:
        a dictionary with variable name as key and :class:`numpy.ndarray` as values
    """

    # matching between internal variable names and column headers in data file
    var2colheader = {'azi': 'Az(deg)', 'ele': 'El(deg)', 'T_amb': 'TkBB(K)',
                     'T': 'Tamb(K)', 'RH': 'Rh(%)', 'p': 'Pres(mb)',
                     'IRT': 'Tir(K)', 'rainflag': 'Rain',
                     'record_nb': 'Record', 'quality': 'DataQuality'}
    # rec type 40 (aux=met+irt)
    # Tamb(K),Rh(%),Pres(mb),Tir(K),Rain,DataQuality
    # rec type 50 (mwr)
    # Az(deg),El(deg),TkBB(K),Ch....,DataQuality

    data = {}
    for ind, hd in enumerate(header):
        for varname, colhead in var2colheader.items():
            if simplify_header(hd) == simplify_header(colhead):
                data[varname] = data_raw[:, ind].astype(float)
    return data


def get_mwr(data_raw, header, only_observed_freq=True):
    """extract the microwave radiometer brightness temperatures and frequencies from data_raw using header

    Args:
        data_raw: raw data as :class:`numpy.ndarray` object
        header: column header belonging to data_raw
        only_observed_freq: if True only frequencies with non-NaN observations are returned. Defaults to True.
    Returns:
        the tuple (brightness_temperature, frequency) where both elements are a :class:`numpy.ndarray`
    """

    pattern_mwr_lower = 'ch '  # pattern that stripped lowered column header must match to be recognised as MWR

    # find indices of MWR data and their frequency from header
    ind_mwr = []
    freq = []
    for ind, colhead in enumerate(header):
        if pattern_mwr_lower == colhead[0:3].lower():
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
