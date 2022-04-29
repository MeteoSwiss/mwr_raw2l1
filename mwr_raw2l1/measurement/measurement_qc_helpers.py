import ephem
import numpy as np

from mwr_raw2l1.errors import UnknownManufacturer
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_construct_helpers import drop_duplicates


def check_receiver_sanity(data, channel):
    """check the receiver sanity flag(s) in data

    Args:
        data: dataset, commonly Measurement.data
        channel: channel index for which to check the sanity flag (only used for RPG)
    Returns:
        tuple containing:
            mask_fail: None if check_applied=False, otherwise array of size (time,) set True where quality is bad
            check_applied (bool): True if check has been applied, False if check could not be applied (not enough info)
    """
    if data['mfr'] == 'attex':
        logger.info('Cannot check receiver sanity for Attex as no status variable is in data file')
        return None, False
    elif data['mfr'] == 'radiometrics':
        return flag_check(data, 'quality', 1, channel=None)
    elif data['mfr'] == 'rpg':
        return flag_check(data, 'channel_quality_ok', 0, channel)  # exclusively base check on channel_qality_ok
        # could add checks for noisediode_ok_kband, noisediode_ok_vband, Tstab_ok_kband, Tstab_ok_vband, Tstab_ok_amb
        # TODO: would better base this check on data['alarm'] present in all datasets. should add additional checks for
        #  channel ok to func for all inst types based also on a inst_config entry channels_to_ignore or the like
    UnknownManufacturer("known manufacturers for this method are ['attex', 'radiometrics', 'rpg'] "
                        "but data['mfr']={}".format(data['mfr']))


def check_rain(data):
    """check the receiver's rain flag in data

    Args:
        data: dataset, commonly Measurement.data
    Returns:
        tuple containing:
            mask_fail: None if check_applied=False, otherwise array of size (time,) set True where rain is detected
            check_applied (bool): True if check has been applied, False if check could not be applied (not enough info)
    """
    if data['mfr'] == 'attex':
        logger.info('Cannot flag rain for Attex as this is not returned by the instruments')
        return None, False
    elif data['mfr'] == 'radiometrics':
        return flag_check(data, 'rainflag', 1)
    elif data['mfr'] == 'rpg':
        return flag_check(data, 'rainflag', 1)
    else:
        UnknownManufacturer("known manufacturers for this method are ['attex', 'radiometrics', 'rpg'] "
                            "but data['mfr']={}".format(data['mfr']))


def check_sun(data, delta_ele, delta_azi):
    """check if sun is in beam within the tolerances 'delta_ele', 'delta_azi' ( abs(data['ele'] - ele_sun) < delta_ele )

    Args:
        data: :class:`xarray.Dataset`, commonly Measurement.data
        delta_ele:
    Returns:
        tuple containing:
            mask_fail: None if check_applied=False, otherwise array of size (time,) set True where sun is in beam
            check_applied (bool): True if check was applied, False if check could not be applied (no ele/azi in data)
    """
    if 'azi' not in data or 'ele' not in data:
        logger.warning("Cannot set solar flag as 'azi' or 'ele' is missing in data.")
        return None, False
    if data.azi.isnull().any() or data.ele.isnull().any():
        logger.warning("Cannot set solar flag as NaN was found in 'azi' or 'ele'.")
        return None, False

    ele_sun, azi_sun = orbit_position_interp(data)  # additional keyword arg body='moon' could be used for lunar flag
    mask = np.logical_and(np.abs(data.ele - ele_sun) < delta_ele,  np.abs(data.azi - azi_sun) < delta_azi)
    return mask, True


def orbit_position_interp(data, delta_t=300, **kwargs):
    """wrapper to :func:`orbit_position` doing orbit calculations only each 'delta_t' seconds and interpolate to time"""

    time_rough = np.append(np.arange(data['time'][0].values, data['time'][-1].values, np.timedelta64(delta_t, 's')),
                           data['time'][-1].values)  # include also last time to span full grid for following interp
    data_rough = drop_duplicates(data.sel(time=time_rough, method='nearest'), 'time')
    ele_rough, azi_rough = orbit_position(data_rough, **kwargs)

    # append to rough dataset and interpolate to time vector of original dataset
    data_rough['sun_ele'] = (('time',), ele_rough)
    data_rough['sun_azi'] = (('time',), azi_rough)
    ele = data_rough.sun_ele.interp(time=data.time).values
    azi = data_rough.sun_azi.interp(time=data.time).values

    return ele, azi


def orbit_position(data, body='sun'):
    """calculate orbit position of sun or moon for instrument position at each time in 'data' using :class:`ephem`

    Args:
        data: :class:`xarray.Dataset`, commonly Measurement.data
        body (optional): name of astronomical body to calculate orbit from ('sun' or 'moon'). Defaults to 'sun'
    Returns:
        tuple containing:
            ele: :class:`numpy.ndarray` of elevations of the body for each time step
            azi: :class:`numpy.ndarray` of azimuths of the body for each time step
    """
    obs = ephem.Observer()
    if body == 'sun':
        obj = ephem.Sun()
    elif body == 'moon':
        obj = ephem.Moon()
    else:
        raise NotImplementedError("function only implemented for 'body' in ['sun', 'moon']")

    ele = np.full(data['time'].shape, np.nan)
    azi = np.full(data['time'].shape, np.nan)
    for ind, time in enumerate(data['time']):
        # observer settings
        obs.lat = str(data['lat'][ind].values)  # needs to be string to be interpreted as degrees
        obs.lon = str(data['lon'][ind].values)  # needs to be string to be interpreted as degrees
        obs.elevation = data['altitude'][ind].values
        obs.date = str(time.dt.strftime('%Y/%m/%d %H:%M:%S').values)

        # get object's position in degrees
        obj.compute(obs)
        ele[ind] = np.rad2deg(obj.alt)
        azi[ind] = np.rad2deg(obj.az)

    return ele, azi


def flag_check(data, varname, value, channel=None):
    """check if flag with 'varname' in 'data' matches 'value'

    Args:
        data: dataset, commonly Measurement.data
        varname: name of the variable in 'data'
        value: value that the flag must match so that this function returns True
        channel (optional): channel index for which to check the flag variables of size (time, channels). If set to None
            a variable of size (time,) the sanity flag (only used for RPG). Defaults to None
    Returns:
        tuple containing:
            mask_fail: None if check_applied=False, otherwise array of size (time,) set True where value is 'matched'
            check_applied (bool): True if check has been applied, False if check could not be applied (not enough info)
    """
    if varname in data:
        if channel is None:
            return (data[varname][:] == value), True
        return (data[varname][:, channel] == value), True
    else:
        logger.info("Cannot apply check for '{}' during quality control as variable does not exist".format(varname))
        return None, False
