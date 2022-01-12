import numpy as np


def timedelta2s(t_diff):
    """return number of seconds from numpy timedelta64 object
    Args:
        t_diff: time difference as :class:`numpy.timedelta64' object
    Returns:
        scalar corresponding to number of seconds
    """
    return t_diff / np.timedelta64(1, 's')
