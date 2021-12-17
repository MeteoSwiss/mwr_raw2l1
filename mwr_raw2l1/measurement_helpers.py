import datetime as dt

import numpy as np
import xarray as xr

from mwr_raw2l1.errors import DimensionError
from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.transformations import timedelta2s


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

    # add optional variables as NaN-series to data if not in input data
    for varo in vars_opt:
        if varo not in data:
            data[varo] = np.full_like(data[dims[0]], np.nan)
            logger.info('Optional variable {} not found in input data. Will create a all-NaN placeholder'.format(varo))

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
        out[src] = drop_duplicates(out[src], dim='time')  # remove duplicate measurements
    return out


########################################################################################################################
# scan transformations                                                                                                 #
########################################################################################################################
def scan_endtime_to_time(endtime, n_angles, time_per_angle=17):
    """
    RPG scan files only have one timestamp per scan. This function returns the approximate timestamp for the observation
    at each angle

    Args
        endtime : numpy array of datetime64 or single datetime.datetime.
            Corresponds ot the single timestamp saved with each angle scan. Assumed as the end time of the scan
        n_angles : number of angles per scan.
        time_per_angle : total time for scanning one angle inluding integration time and the time for moving the mirror.
            Indicated in seconds. The default is 17.

    Returns:
        time : np.array of datetime.datetime objects. list of timestamps (end of integration) for each observed angle
    """

    # TODO: add test to check that brt and blb times do not overlap (or think about it)
    if isinstance(endtime, dt.datetime):
        endtime = np.array([endtime])
        def timedelta_method(seconds): return dt.timedelta(seconds=seconds)
    else:
        def timedelta_method(seconds): return np.timedelta64(int(seconds*1000), 'ms')  # use ms as timedelta needs int

    delta = [timedelta_method(n * time_per_angle) for n in reversed(range(n_angles))]
    delta = np.array(delta)

    endtime = endtime.reshape(len(endtime), 1)  # for letting numpy broadcast along dimension 1
    time = endtime - delta  # calculate time for each scan position (matrix)
    time = time.reshape((-1,))  # make one-dimenional vector out of time matrix

    return time


def scantime_from_aux(blb, hkd=None, brt=None):
    """determine time vector of each elevation in scan using scan_endtime_to_time infering scan duration from aux data

    Args:
        blb: xarray.Dataset of the scan observations
        hkd (optional): dataset of housekeeping data.
        brt (optional): dataset of zenith observation data
    """

    time_scan = blb['time'].values
    n_ele = len(blb['scan_ele'].values)

    endtime2time_params = dict(endtime=time_scan, n_angles=n_ele)
    if hkd is not None and 'BLscan_active' in hkd:
        time_scan_active = hkd.time[hkd.BLscan_active.values == 1].values
        time_zen_active = hkd.time[hkd.BLscan_active.values == 0].values

        if len(blb.time) > 1:  # more than one scan in blb. sure that last one is complete
            time_last_scan_active = time_scan_active[
                np.logical_and(time_scan_active > blb.time[-2].values, time_scan_active <= blb.time[-1].values)]
            scan_duration = timedelta2s(time_last_scan_active[-1] - time_last_scan_active[0])
            endtime2time_params['time_per_angle'] = scan_duration / n_ele
        elif time_scan_active[0] > time_zen_active[0]:  # sure to have full scan at beginning of hkd
            scan_duration = timedelta2s(blb.time[0].values - time_scan_active[0])
            endtime2time_params['time_per_angle'] = scan_duration / n_ele
        else:
            logger.warning(
                'Cannot infer scan duration as first scan might extend to previous period. Using default values')

    elif brt is not None:
        # less accurate than hkd because things happen before scan starts (e.g. ambload obs).
        # Assume after last hkd measure it takes 2x time_per_angle before first scanobs ends.
        if brt.time[0] < blb.time[-1]:
            diff_end_blb_brt = timedelta2s(
                blb.time[-1].values - brt.sel(time=blb['time'][-1], method='pad').time.values)
            endtime2time_params['time_per_angle'] = diff_end_blb_brt / (n_ele+2)
        else:
            logger.warning(
                'Cannot infer scan duration as first scan might extend to previous period. Using default values')

    return scan_endtime_to_time(**endtime2time_params)


def scan_to_timeseries_from_aux(blb, *args, **kwargs):
    """Transform scanning datasete to time series of Tb spectra and temperatures flattening the elevation dimension.

    The time vector of each elevation in scan comes from scan_endtime_to_time inferring scan duration from aux data

    Args:
        blb: xarray.Dataset of the scan observations (BLB)
        *args/**kwargs: auxiliary datasets (HKD, BRT) passed on to scan_endtime_to_time
    """
    time_all_angles = scantime_from_aux(blb, *args, **kwargs)
    # TODO: use the following code to reformat the dimensions
    #
    # n_freq = data['n_freq']
    # n_ele = data['n_ele']
    # n_scans = data['n_scans']
    #
    # tb_tmp = data['Tb_scan'].swapaxes(0, 1)  # swap dim to (freq, time, ele)
    # data['Tb'] = tb_tmp.reshape(n_freq, n_scans * n_ele, order='C').transpose()
    #
    # data['T'] = data['T_per_scan'].repeat(n_ele)  # repeat to have one T value for each new time
    #
    # # transform single vector of elevations to time series of elevations
    # data['ele'] = np.tile(data['scan_ele'], data['n_scans'])

    return blb


def scan_to_timeseries_from_dict(data, *args, **kwargs):
    """transform scans to time series of spectra and temperatures

    Args:
        data: dictioinary containing the scan observations (BLB)
        *arrgs/**kwargs: optional parameters for scan_endtime_to_time
    """
    n_freq = data['n_freq']
    n_ele = data['n_ele']
    n_scans = data['n_scans']

    tb_tmp = data['Tb_scan'].swapaxes(0, 1)  # swap dim to (freq, time, ele)
    data['Tb'] = tb_tmp.reshape(n_freq, n_scans * n_ele, order='C').transpose()

    data['T'] = data['T_per_scan'].repeat(n_ele)  # repeat to have one T value for each new time

    # transform single vector of elevations to time series of elevations
    data['ele'] = np.tile(data['scan_ele'], data['n_scans'])

    # time is encoded as end time of scan (same time for all elevations).
    data['time'] = scan_endtime_to_time(data['time'], data['n_ele'])

    return data
