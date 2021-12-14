import datetime as dt

import numpy
import numpy as np
import xarray as xr
from mwr_raw2l1.errors import DimensionError


def make_dataset(data, dims, vars, vars_opt=None):
    """generate a xarray Dataset from 'data' using the dimensions and variables specified

    Args:
        data: dictionary containing the data
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        xarray.Dataset
    """

    # init
    spec = {}
    if vars_opt is None:
        vars_opt = []

    # add dimensions to spec
    for dim in dims:
        spec[dim] = dict(dims=dim, data=data[dim])

    # add optional variables as NaN-series to data
    for varo in vars_opt:
        if varo not in data:
            data[varo] = np.full_like(data[dims[0]], np.nan)
            # TODO: add logger here to give info that varo is not in data

    # add vars to spec
    all_vars = vars + vars_opt
    for var in all_vars:
        nd = np.ndim(data[var])
        if nd > len(dims):
            raise DimensionError(dims, var, nd)
        spec[var] = dict(dims=dims[0:nd], data=data[var])

    return xr.Dataset.from_dict(spec)


def drop_duplicates(ds, dim):
    """drop duplicates from all data in ds for duplicates in dimension vector

    Args:
        ds: xarray Dataset or DataArray
        dim: string indicating the dimension name to check for duplicates
    Returns:
        ds with unique dimension vector
    """

    _, ind = np.unique(ds[dim], return_index=True)  # keep first index but assume duplicate values identical anyway
    return ds.isel({dim: ind})


def rpg_to_datasets(data, dims, vars, vars_opt):
    """generate unique xarray Datasets for each type of observations in 'data' using dimensions and variables specified

    Args:
        data: dictionary of lists containing the obs (obs: a dictionary of variable names and values) for different
            source files of same type
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        dictionary of xarray.Dataset
    """
    out = {}
    for src, data_series in data.items():
        data_act = []
        for dat in data_series:  # make a xarray dataset from the data dict in each class instance
            data_act.append(make_dataset(dat.data, dims[src], vars[src], vars_opt[src]))
        out[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
        out[src] = drop_duplicates(out[src], dim='time')
    return out


def scan_endtime_to_time(endtime, n_angles, inttime=40, idletime=1.4):
    """
    RPG scan files only have one timestamp per scan. This function returns the
    approximative timestamp for the observations at each angle

    Args
        endtime : numpy array of datetime64 or single datetime.datetime.
            Corresponds ot the single timestamp saved with each angle scan. Assumed as the end time of the scan
        n_angles : number of angles per scan.
        inttime : integration time at each angle in seconds. The default is 40.
        idletime : ime duration for moving the pointing to the respective scan position. The default is 1.4.

    Returns:
        time : np.array of datetime.datetime objects. list of timestamps (end of integration) for each observed angle
    """

    if isinstance(endtime, dt.datetime):
        endtime = np.array([endtime])
        def timedelta_method(seconds): return dt.timedelta(seconds=seconds)
    else:
        def timedelta_method(seconds): return np.timedelta64(int(seconds*1000), 'ms')  # use ms as timedelta needs int

    delta = [timedelta_method(n * (inttime + idletime)) for n in reversed(range(n_angles))]
    delta = np.array(delta)

    endtime = endtime.reshape(len(endtime), 1)  # for letting numpy broadcast along dimension 1
    time = endtime - delta
    time = time.reshape((-1,))

    return time


def scan_to_timeseries_from_aux(blb, brt, hkd=None):

    # determine scan duration
    time_scan = blb['time'].values
    n_ele = len(blb['scan_ele'].values)
    time_per_ele = scan_endtime_to_time(time_scan, n_ele)
    # TODO: better infer optional paramters to scan_endtime_to_time from brt (or hkd)
    # find last time in brt before scan: brt.sel(time=blb['time'][ind_act], method='pad')
    # find first time in brt after scan: brt.sel(time=blb['time'][ind_act], method='backfill')
    # ind_act = 0 (-1) might cause an error with pad (backfill)
    # don't forget to remove elevation dimension

    # TODO: use scan_to_timeseries here

    # TODO: return updated brt


def scan_to_timeseries(data):
    """transform scans to time series of spectra and temperatures"""
    # TODO find a place where this function should go (maybe reader_rpg_helpers and call after read in also hkd)
    n_freq = data['n_freq']
    n_ele = data['n_ele']
    n_scans = data['n_scans']

    tb_tmp = data['Tb_scan'].swapaxes(0, 1)  # swap dim to (freq, time, ele)
    data['Tb'] = tb_tmp.reshape(n_freq, n_scans * n_ele, order='C').transpose()

    data['T'] = data['T_per_scan'].repeat(n_ele)  # repeat to have one T value for each new time

    # transform single vector of elevations to time series of elevations
    data['ele'] = np.tile(data['scan_ele'], data['n_scans'])

    # time is encoded as end time of scan (same time for all elevations). need to transform to time series
    # data['time'] = scan_endtime_to_time(data['time'], data['n_ele'])  # TODO: vectorise scan starttime_to_time (and write test)