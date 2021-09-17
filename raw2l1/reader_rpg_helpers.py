"""
helper functions for the module reader_rpg
"""
import numpy as np
import datetime as dt


def get_binary(filename):
    """return the entire content of the binary file as binary stream"""
    with open(filename, 'rb') as f:
        return f.read()
# TODO: ask Volker if it is ok to declare get_binary outside of any class (pretty general in my eyes). If yes, should it go to helper functions module


def interpret_time(time_in):
    """translate the time format of RPG files to datetime object"""
    posix_offset = dt.datetime.timestamp(dt.datetime(2001, 1, 1))  # offset between RPG and POSIX time in seconds

    scalar_input = False
    if np.isscalar(time_in):
        time_in = np.array([time_in])
        scalar_input = True

    times = [dt.datetime.fromtimestamp(x + posix_offset) for x in time_in]
    out = np.array(times)

    if scalar_input:
        out = out[0]

    return out


def interpret_angle(x, version):
    """
    translate the angle encoding from RPG to elevation and azimuth in degrees

    Parameters
    ----------
    x : float
        RPG angle.
    version : int
        version of RPG angle encoding:
        1: sign(ele) * (abs(ele)+1000*azi)
        2: digits 1-5 = elevation*100; digits 6-10 = azimuth*100

    Returns
    -------
    ele : float
        elevation
    azi : float
        azimuth

    """
    scalar_input = False  # TODO: ask Volker about this code copy between interpret_angle and interpret_time
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
        raise NotImplementedError('Known versions for angle encoding are 1 and 2, but received %f' % version)

    if scalar_input:  # TODO: ask Volker about this code copy between interpret_angle and interpret_time
        ele = ele[0]
        azi = azi[0]

    return ele, azi


def interpret_coord(x, version=2):  # TODO: Ask Harald how to find out which coord version used. In manual 06/2020 version=1 is described
    """
    Translate coordinate encoding from RPG to degrees with decimal digits.

    Parameters
    ----------
    x : float
    version : int
        version of RPG angle encoding:
        1: latitude of lognitude in fomrat (-)DDDMM.mmmm where DDD is degrees,
        MM is minutes and mmmm is the decimal fraction of MM
        2: latitude and longitude already in decimal degrees. function does nothing

    Returns
    -------
    out : float
        latitude or longitude in format decimal degrees.

    """

    if version == 1:
        degabs = np.abs(x) // 100
        minabs = np.abs(x) - degabs * 100
        return np.sign(x) * (degabs + minabs / 60)
    elif version == 2:
        return x
    else:
        raise NotImplementedError('Known versions for coordinates encoding are 1 and 2, but received %f' % version)


def interpret_hkd_contents_code(contents_code_integer, bit_order):
    """interpret the integer contents from HKD files and return dict of contents variables"""

    bit_order = interpret_bit_order(bit_order)
    contents_code_int8 = np.array([contents_code_integer]).view(np.uint8)
    hkdselbits = np.unpackbits(contents_code_int8, bitorder=bit_order)

    out = {'has_coord': hkdselbits[0],
           'has_T': hkdselbits[1],
           'has_stability': hkdselbits[2],
           'has_flashmemoryinfo': hkdselbits[3],
           'has_qualityflag': hkdselbits[4],
           'has_statusflag': hkdselbits[5]}

    return out


def interpret_statusflag_series(flag_series, bit_order):
    """interpret_statusflag applied to a series of flags"""
    all_flagdicts = []
    for flag in flag_series:
        all_flagdicts.append(interpret_statusflag(flag, bit_order))

    out = all_flagdicts[0]  # FIXME: return a dict with lists inside, first element is just for testing
    # TODO: ask Volker how to return a dict of lists from a list of dicts

    return out


def interpret_statusflag(flag_integer, bit_order):
    """interpret the integer statusflag from HKD files and return dict of status variables"""

    n_freq_kband = 7  # number of frequency channels in K-band receiver
    n_freq_vband = 7  # number of frequency channels in V-band receiver

    bit_order = interpret_bit_order(bit_order)
    flag_int8 = np.array([flag_integer]).view(np.uint8)
    statusflagbits = np.unpackbits(flag_int8, bitorder=bit_order)

    tstabflag_kband = statusflagbits[24] + 2 * statusflagbits[25]
    tstabflag_vband = statusflagbits[26] + 2 * statusflagbits[27]

    out = {'channel_quality_ok_kband': statusflagbits[0:n_freq_kband],
            'channel_quality_ok_vband': statusflagbits[8:(8 + n_freq_vband)],
            'rainflag': statusflagbits[16],
            'blowerspeed_status': statusflagbits[17],
            'BLscan_active': statusflagbits[18],
            'tipcal_active': statusflagbits[19],
            'gaincal_active': statusflagbits[20],
            'noisecal_active': statusflagbits[21],
            'noisediode_ok_kband': statusflagbits[22],
            'noisediode_ok_vband': statusflagbits[23],
            'Tstab_ok_kband': interpret_tstab_flag(tstabflag_kband),
            'Tstab_ok_vband': interpret_tstab_flag(tstabflag_vband),
            'recent_powerfailure': statusflagbits[28],
            'Tstab_ok_amb': interpret_tstab_flag(statusflagbits[29]),  # 1:ok, 0:not ok because sensors differ by >0.3 K
            'noisediode_on': statusflagbits[30]}

    return out


def interpret_tstab_flag(flag):
    """interpret temperature stability flag and return a flag saying stability ok (1), not ok (0) or unknown (NaN)"""
    if flag == 0:  # unknown, not enough data samples recorded yet
        tstab_ok = np.nan
    elif flag == 1:  # stability ok
        tstab_ok = 1
    elif flag == 2:  # not sufficiently stable
        tstab_ok = 0
    else:
        ValueError('can interpret RPG temperature stability flag with values 0, 1 or 2 but received ' + flag)

    return tstab_ok


def interpret_bit_order(bit_order):
    """interpret bit_order for use in numpy's unpackbits so that it also '>' and '<' can be used"""
    if bit_order == 'little' or bit_order == 'big':
        return bit_order
    elif bit_order == '<':
        return 'little'
    elif bit_order == '>':
        return 'big'
    else:
        raise ValueError("argument bit_order can receive '<', '>', 'little' or 'big' but got " + bit_order)


def scan_starttime_to_time(starttime, n_angles, inttime=40, caltime=40, idletime=1.4):
    """
    RPG scan files only have one timestamp per scan. This function returns the
    approximative timestamp for the observations at each angle

    Parameters
    ----------
    scan_starttime : datetime.datetime
        the single timestamp saved with the angle scan. Assumed as the start
        time of the scan
    n_angles : int
        number of angles per scan.
    inttime : int, optional
        integration time at each angle in seconds. The default is 40.
    caltime : int, optional
        integration time for the internal calibration before each scan [s].
        The default is 40.
    idletime : float, optional
        time duration for moving the pointing to the repective scan poisiton.
        The default is 1.4.

    Returns
    -------
    time : np.array of datetime.datetime objects
        list of timestamps for each observed angle

    """

    time = np.empty(n_angles, dtype=np.dtype(dt.datetime))
    time[0] = starttime + dt.timedelta(seconds=caltime)
    for n in range(1, n_angles):
        time[n] = time[n - 1] + dt.timedelta(seconds=caltime + idletime)

    return time

