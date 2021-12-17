import numpy as np


def timedelta2s(t_diff):
    """return number of seconds from numpy timedelta64 object
    Args:
        t_diff: numpy timedelta64
    Returns:
        scalar corresponding to number of seconds
    """
    return t_diff / np.timedelta64(1, 's')
