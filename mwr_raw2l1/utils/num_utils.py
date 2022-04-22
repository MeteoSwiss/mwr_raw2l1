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
    """check if n-th bit is set (==1) in x

    Args:
        x: integer or :class:`numpy.ndarray` of integers
        nth_bit: position of investigated bit (0, 1, 2, ...)
    Returns:
        boolean or boolean array denoting whether the nth_bit is set in x.
    Examples:
        >>> isbitset(3, 0)
            True
        >>> isbitset(2, 0)
            False
    """
    if nth_bit < 0:
        raise ValueError('position of bit cannot be negative')
    mask = 1 << nth_bit
    return x & mask > 0


def setbit(x, nth_bit):
    """set n-th bit (i.e. set to 1) in an integer or array of integers

    Args:
        x: integer or :class:`numpy.ndarray` of integers
        nth_bit: position of bit to be set (0, 1, 2, ..)
    Returns:
        integer or array of integers where n-th bit is set while all other bits are kept as in input x
    Examples:
        >>> setbit(0, 1)
            2
        >>> setbit(3, 2)
            7
    """
    if nth_bit < 0:
        raise ValueError('position of bit cannot be negative')
    mask = 1 << nth_bit
    return x | mask


def unsetbit(x, nth_bit):
    """unset n-th bit (i.e. set to 0) in an integer or array of integers

    Args:
        x: integer or :class:`numpy.ndarray` of integers
        nth_bit: position of bit to be set (0, 1, 2, ..)
    Returns:
        integer or array of integers where n-th bit is unset while all other bits are kept as in input x
    Examples:
        >>> unsetbit(7, 2)
            3
        >>> unsetbit(8, 2)
            8
    """
    if nth_bit < 0:
        raise ValueError('position of bit cannot be negative')
    mask = 1 << nth_bit
    return x & ~mask
