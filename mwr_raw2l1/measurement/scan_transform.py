"""collection of functions for transforming a scanning observation with elevation dim to a flat time series"""

import datetime as dt

import numpy as np

from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.transformations import timedelta2s


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
    """determine time vector of each elevation in scan using scan_endtime_to_time inferring scan duration from aux data

    If none of the optional arguments is provided default scan duration form scan_endtime_to time is used

    Args:
        blb: xarray.Dataset of the scan observations
        hkd (optional): dataset of housekeeping data.
        brt (optional): dataset of zenith observation data
    Returns:
         np.array of datetime.datetime objects. list of timestamps (end of integration) for each observed angle
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


def scan_to_timeseries(blb, *args, **kwargs):
    """Transform scanning datasete to time series of Tb spectra and temperatures flattening the elevation dimension.

    The time vector of each elevation in scan comes from scan_endtime_to_time inferring scan duration from aux data

    Args:
        blb: xarray.Dataset of the scan observations (BLB)
        *args/**kwargs: auxiliary datasets (HKD, BRT) passed on to scan_endtime_to_time
    Returns:
        blb with elevation-dimension transformed to time series
    """

    time_dim = 'time'
    ele_dim = 'scan_ele'
    n_ele = len(blb[ele_dim])
    n_scans = len(blb[time_dim])

    # transform time vector and assign as temporary dimension
    time_all_angles = scantime_from_aux(blb, *args, **kwargs)
    blb = blb.assign_coords({'time_tmp': time_all_angles})

    # reshape data variables to correct dimension
    for var in blb.data_vars:
        var_tmp = blb[var].values
        if len(blb[var].dims) == 3 and blb[var].dims[-1] == ele_dim and blb[var].dims[0] == time_dim:  # 3 dimensional
            var_tmp = var_tmp.swapaxes(0, 1)  # swap dim to (xxx, time, ele) where xxx is usually frequency
            var_tmp = var_tmp.reshape(-1, n_scans*n_ele, order='C').transpose()
            dims_act = ('time_tmp', blb[var].dims[1])
        elif len(blb[var].dims) == 1 and blb[var].dims[0] == time_dim:
            var_tmp = var_tmp.repeat(n_ele)
            dims_act = ('time_tmp',)
        else:
            raise NotImplementedError('transformation only implemented for 1d timeseries and 3d variables with'
                                      + ' time as first and elevation as third dimension')
        blb = blb.drop_vars(var)  # remove original variable from dataset
        blb = blb.assign({var: (dims_act, var_tmp)})  # assign reshaped variable to dataset

    # reshape elevation remove as dimension and assign as variable
    ele_tmp = blb[ele_dim].values
    ele_tmp = np.tile(ele_tmp, n_scans)
    blb = blb.drop_dims(ele_dim)
    blb = blb.assign({'ele': (('time_tmp',), ele_tmp)})

    # replace old time dimension by the freshly created one
    blb = blb.drop_dims(time_dim)
    blb = blb.rename({'time_tmp': time_dim})

    return blb


def scan_to_timeseries_from_dict(data, *args, **kwargs):
    """transform scans to time series of spectra and temperatures starting from dict.

    Not routinely used anymore. More hard coding than for scan_to_timeseries

    Args:
        data: dictioinary containing the scan observations (BLB)
        *arrgs/**kwargs: optional parameters for scan_endtime_to_time
    """
    n_freq = data['n_freq']
    n_ele = data['n_ele']
    n_scans = data['n_scans']

    tb_tmp = data['Tb'].swapaxes(0, 1)  # swap dim to (freq, time, ele)
    data['Tb'] = tb_tmp.reshape(n_freq, n_scans * n_ele, order='C').transpose()

    data['T'] = data['T'].repeat(n_ele)  # repeat to have one T value for each new time

    # transform single vector of elevations to time series of elevations
    data['ele'] = np.tile(data['scan_ele'], data['n_scans'])

    # time is encoded as end time of scan (same time for all elevations).
    data['time'] = scan_endtime_to_time(data['time'], data['n_ele'])

    return data
