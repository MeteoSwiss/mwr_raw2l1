from mwr_raw2l1.errors import UnknownManufacturer
from mwr_raw2l1.log import logger


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
