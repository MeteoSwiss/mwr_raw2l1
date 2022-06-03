import numpy as np


def channels2receiver(freq, band_limits=None):
    """attribute 1-based receiver numbers (1, 2, ...) to frequency channels

    Args:
        freq: frequency vector in GHz
        band_limits (optional): limit frequencies (in GHz) between different receivers. Need max(band_limits)<max(freq)
    """
    if band_limits is None:
        band_limits = [0, 1, 2, 4, 8, 12, 40, 75, 110, 300, np.inf]

    # attribute channels to different bands
    rec_nb_tmp = np.full(np.shape(freq), np.nan)
    for ind, f in enumerate(freq):
        for n, lim in enumerate(band_limits):
            if f < lim:
                rec_nb_tmp[ind] = n
                break

    # count for receivers only if existing
    _, rec_nb_0 = np.unique(rec_nb_tmp, return_inverse=True)  # zero-based receiver number

    return rec_nb_0 + 1


if __name__ == '__main__':
    out = channels2receiver([22.2, 23.0, 23.8, 25.4, 26.2, 27.8, 31.4, 51.3, 52.3, 53.9, 54.9, 56.7, 57.3, 58.0, 183])
    print(out)
