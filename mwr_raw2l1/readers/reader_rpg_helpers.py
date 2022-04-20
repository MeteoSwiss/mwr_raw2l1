"""
helper functions for the module reader_rpg
"""
import datetime as dt

import numpy as np

from mwr_raw2l1.errors import UnknownFlagValue, WrongInputFormat


def interpret_time(time_in):
    """translate the time format of RPG files to datetime object"""
    # offset between RPG and POSIX time in seconds. Care: datetime base must be in UTC, hence tzinfo muxt be given.
    posix_offset = dt.datetime.timestamp(dt.datetime(2001, 1, 1, tzinfo=dt.timezone(dt.timedelta(0))))

    scalar_input = False
    if np.isscalar(time_in):
        time_in = np.array([time_in])
        scalar_input = True

    times = [dt.datetime.utcfromtimestamp(x + posix_offset) for x in time_in]
    out = np.array(times)

    if scalar_input:
        out = out[0]

    return out


def interpret_angle(x, version):
    """translate the angle encoding from RPG to elevation and azimuth in degrees

    Args:
        x: RPG angle.
        version: version of RPG angle encoding:
            1: sign(ele) * (abs(ele)+1000*azi)
            2: digits 1-5 = elevation*100; digits 6-10 = azimuth*100
    Returns:
        elevation, azimuth
    """
    scalar_input = False
    if np.isscalar(x):
        x = np.array([x])
        scalar_input = True

    if version == 1:
        ele_offset = np.zeros(x.shape)
        ind_offset_corr = (x >= 1e6)
        ele_offset[ind_offset_corr] = 100
        x[ind_offset_corr] -= 1e6

        azi = (np.abs(x) // 100) / 10  # assume azi and ele are measured in 0.1 degree steps
        ele = x - np.sign(x) * azi * 1000 + ele_offset
    elif version == 2:
        ele = np.sign(x) * (np.abs(x) // 1e5) / 100
        azi = (np.abs(x) - np.abs(ele) * 1e7) / 100
    else:
        raise NotImplementedError('Known versions for angle encoding are 1 and 2, but received {:f}'.format(version))

    if scalar_input:
        ele = ele[0]
        azi = azi[0]

    return ele, azi


def interpret_coord(x, version=2):
    # TODO: Ask Harald how to find out which coord version used. In manual 06/2020 version=1 is described
    """Translate coordinate encoding from RPG to degrees with decimal digits.

    Args:
        x: float encoding latitude of longitude coordinate in RPG binaries
        version: version of RPG coordinate encoding:
            1: latitude of lognitude in fomrat (-)DDDMM.mmmm where DDD is degrees, MM is minutes and mmmm is the decimal
                fraction of MM
            2: latitude and longitude already in decimal degrees, function does nothing.
    Returns:
        latitude or longitude in format decimal degrees.
    """

    if version == 1:
        degabs = np.abs(x) // 100
        minabs = np.abs(x) - degabs * 100
        return np.sign(x) * (degabs + minabs / 60)
    elif version == 2:
        return x
    else:
        raise NotImplementedError('Known versions for coordinates encoding are 1 and 2, but received {:f}'.format(
            version))


def interpret_met_auxsens_code(auxsenscode):
    """interpret integer code for the availability of auxiliary sensors in MET files, return dict of contents vars"""
    auxsenscode_int8 = np.uint8(auxsenscode)
    auxsensbits = np.unpackbits(auxsenscode_int8, bitorder='little')
    if auxsensbits is None:
        out = {'has_windspeed': 0,
               'has_winddir': 0,
               'has_rainrate': 0}
    else:
        out = {'has_windspeed': auxsensbits[0],
               'has_winddir': auxsensbits[1],
               'has_rainrate': auxsensbits[2]}

    return out


def interpret_hkd_contents_code(contents_code_integer):
    """interpret the integer contents code from HKD files and return dict of contents variables"""

    contents_code_int8 = np.array([contents_code_integer]).view(np.uint8)
    hkdselbits = np.unpackbits(contents_code_int8, bitorder='little')

    out = {'has_coord': hkdselbits[0],
           'has_T': hkdselbits[1],
           'has_stability': hkdselbits[2],
           'has_flashmemoryinfo': hkdselbits[3],
           'has_qualityflag': hkdselbits[4],
           'has_statusflag': hkdselbits[5]}

    return out


def interpret_statusflag(flag_integer):
    """interpret the statusflag from HKD files and return a dict of status variables (input time series or scalar)"""

    n_freq_kband = 7  # number of frequency channels in K-band receiver
    n_freq_vband = 7  # number of frequency channels in V-band receiver

    statusflagbits = flag_int2bits(flag_integer)

    # interpret the different bits according to the manual
    tstabflag_kband = statusflagbits[:, 24] + 2 * statusflagbits[:, 25]
    tstabflag_vband = statusflagbits[:, 26] + 2 * statusflagbits[:, 27]
    out = {
        'channel_quality_ok_kband': statusflagbits[:, 0:n_freq_kband],
        'channel_quality_ok_vband': statusflagbits[:, 8:(8 + n_freq_vband)],
        'rainflag': statusflagbits[:, 16],
        'blowerspeed_status': statusflagbits[:, 17],
        'BLscan_active': statusflagbits[:, 18],
        'tipcal_active': statusflagbits[:, 19],
        'gaincal_active': statusflagbits[:, 20],
        'noisecal_active': statusflagbits[:, 21],
        'noisediode_ok_kband': statusflagbits[:, 22],
        'noisediode_ok_vband': statusflagbits[:, 23],
        'Tstab_ok_kband': interpret_tstab_flag(tstabflag_kband),
        'Tstab_ok_vband': interpret_tstab_flag(tstabflag_vband),
        'recent_powerfailure': statusflagbits[:, 28],
        'Tstab_ok_amb': interpret_tstab_flag(statusflagbits[:, 29]),
        'noisediode_on': statusflagbits[:, 30]}

    return out


def interpret_scanflag(flag_integer):
    """interpret flag of BLB scan

    Args:
        flag_integer: scanflag from BLB as integer. When transformed to bit, first bit interpreted as rainflag while
            2nd/3rd encodes scan time (see notes)
    Returns:
        Dictionary with keys 'rainflag' and 'scan_quadrant'

    Notes:
        ===================   ======================   ============================
        2nd/3rd bit (input)   scan_quadrant (output)   description
        ===================   ======================   ============================
        0/0                   1                        first quadrant
        0/1                   2                        second quadrant
        1/0                   0                        average over both quadrants
        ===================   ======================   ============================
    """

    scanflagbits = flag_int2bits(flag_integer)
    int_quadr = scanflagbits[:, 1] + 2 * scanflagbits[:, 2]
    out = {
        'rainflag': scanflagbits[:, 0],
        'scan_quadrant': interpret_quadrant_int(int_quadr)}

    return out


def interpret_tstab_flag(flag):
    """interpret temperature stability flag and return a flag saying stability ok (1), not ok (0) or unknown (NaN)

    Notes:
        ==================   =================   ==========================================================
        tstab flag (input)   tstab ok (output)   description
        ==================   =================   ==========================================================
        0                    NaN                 unknown stability (too short measurement series available)
        1                    1                   stability ok
        2                    0                   not ok (T sensors differ by >0.3 K)
        ==================   =================   ==========================================================
    """
    flag2tstab_ok = {0: np.nan, 1: 1, 2: 0}  # correspondence of RPG stability flag (keys) with stability ok (value)
    try:
        if np.isscalar(flag):
            return flag2tstab_ok[flag]
        else:
            return np.array([flag2tstab_ok[el] for el in flag])
    except KeyError as err:
        raise UnknownFlagValue('Expected 0, 1 or 2 for RPG temperature stability flag but found {}'.format(err))


def interpret_quadrant_int(int_quadr):
    """helper function for interpret scanflag for interpreting 2nd and 3rd bit (as int). See documentation from there"""
    int2quadrant = {0: 1, 1: 2, 2: 0}  # correspondence of int(2nd and 3rd bit) (keys) with quadrant (value)
    try:
        if np.isscalar(int_quadr):
            int2quadrant[int_quadr]
        else:
            return np.array([int2quadrant[el] for el in int_quadr])
    except KeyError as err:
        raise UnknownFlagValue('Expected 0, 1 or 2 for scan quadrant encoding but found {}'.format(err))


def interpret_bit_order(bit_order):
    """interpret bit_order for use in :func:`numpy.unpackbits` so that it also '>' and '<' can be used"""
    if bit_order == 'little' or bit_order == 'big':
        return bit_order
    elif bit_order == '<':
        return 'little'
    elif bit_order == '>':
        return 'big'
    else:
        raise ValueError("argument bit_order can receive '<', '>', 'little' or 'big' but got " + bit_order)


def flag_int2bits(flag_integer):
    """transform an integer value to bits. Input can be time series or scalars"""
    # format input
    if len(np.shape(flag_integer)) == 0:  # input is scalar
        flag_integer = np.array([[flag_integer]])
    elif not isinstance(flag_integer, np.ndarray):
        raise WrongInputFormat('input must either be a numpy array or a scalar')
    elif np.ndim(np.squeeze(flag_integer)) > 1:
        raise WrongInputFormat('input can only be vector or scalar but not matrix')
    else:  # input is vector
        flag_integer = np.squeeze(flag_integer)[:, np.newaxis]

    # transform integer (time series) to flag bits
    flag_int8 = flag_integer.view(np.uint8)
    return np.unpackbits(flag_int8, axis=1, bitorder='little')
