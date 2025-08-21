"""collection of functions for transforming a scanning observation with elevation dim to a flat time series"""

import datetime as dt

import numpy as np

from mwr_raw2l1.errors import MWRDataError
from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.num_utils import timedelta2s


def scan_endtime_to_time(endtime, n_angles, time_per_angle=11, from_starttime=False):
    """
    RPG and Attex scan files only have one timestamp per scan. This function returns the approximate timestamp for the
    observation at each angle

    Args:
        endtime (:class:`numpy.ndarray` of :class:`numpy.datetime64` or single :class:`datetime.datetime` object):
            Corresponds ot the single timestamp saved with each angle scan. Assumed as the end time of the scan
        n_angles: number of angles per scan.
        time_per_angle: total time for scanning one angle incl. integration time and the time for moving the mirror.
            Indicated in seconds. The default is 17.
        from_starttime: if True, the timestamps will be calculated assuming the provided time is the start time of 
        the scan, otherwise from the end time. This arise from the change in timestamping operated in HATPRO instruments (TBC)

    Returns:
        time : :class:`numpy.ndarray` of :class:`datetime.datetime` objects of end times for each observed angle
    """

    if isinstance(endtime, dt.datetime):
        endtime = np.array([endtime])
        def timedelta_method(seconds): return dt.timedelta(seconds=seconds)
    else:
        def timedelta_method(seconds):
            # use ms as timedelta needs int. Will truncate to ms what should also avoid rounding errors in tests
            return np.timedelta64(int(seconds*1000), 'ms')

    if from_starttime:
        delta = [timedelta_method(n * time_per_angle) for n in range(n_angles)]
    else:
        delta = [timedelta_method(n * time_per_angle) for n in reversed(range(n_angles))]
    delta = np.array(delta)

    endtime = endtime.reshape(len(endtime), 1)  # for letting numpy broadcast along dimension 1
    if from_starttime:
        time = endtime + delta  # calculate time for each scan position (matrix)
    else:
        time = endtime - delta

    time = time.reshape((-1,))  # make one-dimenional vector out of time matrix

    return time


def scantime_from_aux(blb, hkd=None, brt=None):
    """determine time of each elevation in scan using :func:`scan_endtime_to_time` inferring scan duration from aux data

    If none of the optional arguments is provided default scan duration form :func:`scan_endtime_to_time` is used

    Args:
        blb: :class:`xarray.Dataset` of the scan observations
        hkd (optional): :class:`xarray.Dataset` of housekeeping data
        brt (optional): :class:`xarray.Dataset` of zenith observation data
    Returns:
        vector of timestamps (end of integration) for each observed angle as :class:`numpy.ndarray` of
        :class`datetime.datetime` objects
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
            scan_duration = timedelta2s(time_scan_active[-1] - time_scan_active[0])
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
    
    # TODO: remove the workaround below once we know for sure if time in .BLB is start or end time of the scans.
    if np.abs(timedelta2s(time_scan_active[0] - time_scan[0])) > 50:
        logger.info('Assuming that the time in BLB file is the endtime of the scan: TBC')
    else:
        endtime2time_params = dict(endtime=time_scan, n_angles=n_ele, time_per_angle=endtime2time_params['time_per_angle'], from_starttime=True)
        logger.info('Assuming that the time in BLB file is the starttime of the scan: TBC')
    
    return scan_endtime_to_time(**endtime2time_params)


def scan_to_timeseries(scanobs, time_all_angles):
    """Transform scanning dataset to time series of Tb spectra and temperatures flattening the elevation dimension.

    Args:
        scanobs: :class:`xarray.Dataset` of the scan observations with dimensions time, frequency, scan_ele
        time_all_angles: :class:`numpy.ndarray` indicating the time for each observation at each elevation. Can be
            inferred from :func:`scan_endtime_to_time` or :func:`scantime_from_aux`
    Returns:
        scanobs with elevation-dimension transformed to time series
    """

    time_dim = 'time'
    ele_dim = 'scan_ele'
    n_ele = len(scanobs[ele_dim])
    n_scans = len(scanobs[time_dim])

    # assign time vector for all angles and as temporary dimension
    scanobs = scanobs.assign_coords({'time_tmp': time_all_angles})

    # reshape data variables to correct dimension
    for var in scanobs.data_vars:
        var_tmp = scanobs[var].values
        # 3-dimensional variables (time, freq, ele_dim)
        if len(scanobs[var].dims) == 3 and \
                scanobs[var].dims[-1] == ele_dim and scanobs[var].dims[0] == time_dim:
            var_tmp = var_tmp.swapaxes(0, 1)  # swap dim to (xxx, time, ele) where xxx is usually frequency
            var_tmp = var_tmp.reshape(-1, n_scans * n_ele, order='C').transpose()
            dims_act = ('time_tmp', scanobs[var].dims[1])
        # 1-dimensional variables (time, )
        elif len(scanobs[var].dims) == 1 and scanobs[var].dims[0] == time_dim:
            var_tmp = var_tmp.repeat(n_ele)
            dims_act = ('time_tmp',)
        else:
            raise NotImplementedError('transformation only implemented for 1d timeseries and 3d variables with '
                                      'time as first and elevation as third dimension')
        scanobs = scanobs.drop_vars(var)  # remove original variable from dataset
        scanobs = scanobs.assign({var: (dims_act, var_tmp)})  # assign reshaped variable to dataset

    # reshape elevation remove as dimension and assign as variable
    ele_tmp = scanobs[ele_dim].values
    ele_tmp = np.tile(ele_tmp, n_scans)
    scanobs = scanobs.drop_dims(ele_dim)
    scanobs = scanobs.assign({'ele': (('time_tmp',), ele_tmp)})

    # replace old time dimension by the one covering all angles created in this function
    scanobs = scanobs.drop_dims(time_dim)
    scanobs = scanobs.rename({'time_tmp': time_dim})

    return scanobs


def scan_to_timeseries_from_aux(blb, *args, **kwargs):
    """Transform scanning dataset to time series of Tb spectra and temperatures flattening the elevation dimension.

    The time vector of each elevation in scan comes from scantime_from_aux inferring scan duration from auxiliary data

    Args:
        blb: :class:`xarray.Dataset` of the scan observations (BLB)
        *args: Auxiliary observations (HKD, BRT) as :class:`xarray.Dataset` passed on to :func:`scantime_from_aux`
        **kwargs: Auxiliary observations (HKD, BRT) as :class:`xarray.Dataset` passed on to :func:`scantime_from_aux`
    Returns:
        blb with elevation-dimension transformed to time series
    """
    time_all_angles = scantime_from_aux(blb, *args, **kwargs)
    return scan_to_timeseries(blb, time_all_angles)


def scan_to_timeseries_from_scanonly(scanobs):
    """Transform scanning dataset to time series of Tb spectra and temperatures flattening the elevation dimension.

    The time vector of each elevation is inferred from scanobs assuming that median(interval between scans) is constant
    and corresponds to the time between subsequent scan end times

    Args:
        scanobs: :class:`xarray.Dataset` of the scan observations (e.g. from Attex or from RPG in scan-only mode)
    Returns:
        scanobs with elevation-dimension transformed to time series
    """
    time_scan = scanobs['time'].values
    n_ele = len(scanobs['scan_ele'].values)

    dt_all = np.diff(time_scan)
    scan_duration = np.median(dt_all)
    if scan_duration - dt_all.min() > np.timedelta64(30, 's'):
        raise MWRDataError('highly irregular scan duration in input data, refusing to guess default duration from this')
    time_all_angles = scan_endtime_to_time(time_scan, n_ele, timedelta2s(scan_duration)/n_ele)

    return scan_to_timeseries(scanobs, time_all_angles)


def scan_to_timeseries_from_dict(data, *args, **kwargs):
    """transform scans to time series of spectra and temperatures starting from dict.

    Warning:
        Not routinely used anymore. More hard coding than for :func:`scan_to_timeseries_from_aux`

    Args:
        data: dictioinary containing the scan observations (BLB)
        *args: Auxiliary observations
        **kwargs: Auxiliary observations
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


def scanflag_from_ele(ele, use_ele_diff=False):
    """infer scanflag (0: starring; 1: scanning) from elevation vector

    Args:
        ele: elevation vector as :class:`numpy.ndarray`
        use_ele_diff: if True infer scanflag from differences in ele, if False ele>89 are assumed starring, all others
            as scanning. Defaults to False.
    Returns:
        scanflags as :class:`numpy.ndarray` of same shape as ele
    """

    if use_ele_diff:
        err_msg = 'currently scanflags can only be inferred from assuming ele>89 as starring and all others as scanning'
        raise NotImplementedError(err_msg)
    else:
        return np.where(ele > 89, 0, 1)
