import numpy as np


def timedelta2s(t_diff):
    """return number of seconds from :class:`numpy.timedelta64` object
    Args:
        t_diff: time difference as :class:`numpy.timedelta64` object
    Returns:
        scalar corresponding to number of seconds
    """
    return t_diff / np.timedelta64(1, 's')


def isbitset(x, nth_bit):
    """Check if n-th bit is set (==1) in x.
    Args:
        x: Integer or :class:`numpy.ndarray` of integers.
        nth_bit: Position of investigated bit (0, 1, 2, ...)
    Returns:
        Boolean or boolean array denoting values whether the nth_bit is set.
    Examples:
        >>> isbitset(3, 0)
            True
        >>> isbitset(2, 0)
            False
    """
    if nth_bit < 0:
        raise ValueError('bit number cannot be negative')
    mask = 1 << nth_bit
    return x & mask > 0


def setbit(x, nth_bit):
    """Sets nth bit (i.e. sets to 1) in an integer or array of integers.
    Args:
        x: Integer or :class:`numpy.ndarray` of integers.
        nth_bit: Bit to be set.
    Returns:
        Integer where nth bit is set.
    Examples:
        >>> setbit(0, 1)
            2
        >>> setbit(3, 2)
            7
    """

    if nth_bit < 0:
        raise ValueError('bit number cannot be negative')
    mask = 1 << nth_bit
    x |= mask
    return x
