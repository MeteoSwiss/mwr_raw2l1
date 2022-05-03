import glob
import os
import pickle
from itertools import groupby
from pathlib import Path

import mwr_raw2l1
from mwr_raw2l1.errors import MWRInputError


def abs_file_path(*file_path):
    """
    Make a relative file_path absolute in respect to the mwr_raw2l1 project directory.
    Absolute paths wil not be changed
    """
    path = Path(*file_path)
    if path.is_absolute():
        return path
    return Path(mwr_raw2l1.__file__).parent.parent / path


def get_binary(filename):
    """return the entire content of the binary file as binary stream"""
    with open(filename, 'rb') as f:
        return f.read()


def pickle_load(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def pickle_dump(data, filename):
    with open(filename, 'wb') as f:
        pickle.dump(data, f)


def get_corresponding_pickle(filename_rawdata, path_pickle, legacy_reader=False):
    """get pickled file from previous read-in corresponding to raw data file"""
    suffix = ''
    if legacy_reader:
        suffix = '_legacy'

    fn_and_ext = os.path.splitext(filename_rawdata)
    fn_pickle = fn_and_ext[0] + '_' + fn_and_ext[1][1:].lower() + suffix + '.pkl'
    pickle_file = abs_file_path(path_pickle, fn_pickle)
    if not os.path.isfile(pickle_file):
        raise FileNotFoundError(pickle_file + 'does not exist. Cannot check if data is correct')

    return pickle_load(pickle_file)


def get_files(dir_in, basename, time_start=None, time_end=None):
    """get files in dir_in corresponding to basename.

    If time_start and/or time_end are given only files with end time before/after these are returned.

    Args:
        dir_in: directory where files of the respective instrument are located
        basename: first part of the filename (usually full identifier including wigos-station-id and inst-id)
        time_start (optional): string in format 'yyyymmddHHMM', 'yyyymmddHHMMSS', 'yyyymmdd' or any of the similar
        time_end (optional): analogous to time_start
    Returns:
        list of files in dictionary corresponding to basename and time criteria
    """

    files = glob.glob(os.path.join(dir_in, basename + '*'))

    if time_start is None and time_end is None:
        return files

    # select only files between time_start and time_end
    for file in files[:]:
        fn_date = datestr_from_filename(file)
        if time_start is not None:
            if int(fn_date)/10**len(fn_date) < int(time_start)/10**len(time_start):
                files.remove(file)
                continue
        if time_end is not None:
            if int(fn_date)/10**len(fn_date) > int(time_end)/10**len(time_end):
                files.remove(file)
                continue

    return files


def datestr_from_filename(filename, datestr_format='yyyymmddHHMM'):
    """return date string from filename, assuming it consists of the last digits of the filename before the extension

    Args:
        filename: filename as str. Can contain path and extension.
        datestr_format: format of the date string in the filename. Only used for counting length of date string
    Returns:
        string containing the date in same representation as in the filename
    """
    return os.path.splitext(filename)[0][-len(datestr_format):]


def generate_output_filename(basename, time, ext='nc'):
    """generate filename from basename, ext and end time inferred from data time vector (basename_yyyymmddHHMM.ext)

    Args:
        basename: the first part of the filename without the date
        time: :class:`xarray.DataArray` time vector of the data in :class:`numpy.datetime64` format. Assume to be sorted
        ext (optional): filename extension. Defaults to 'nc'. Empty not permitted.
    """
    return '{}{}.{}'.format(basename, time[-1].dt.strftime('%Y%m%d%H%M').data, ext)


def group_files(files, fileparts_to_ignore):
    """group files in a list of files

    Args:
        files: list of files
        fileparts_to_ignore ('ext', 'suffix'): file parts to ignore for the grouping process
    Returns:
        list of lists with files for which the parts except 'fileparts_to_ignore' are identical
    """
    if fileparts_to_ignore in ['ext', 'extension']:
        pattern_builder = remove_ext
    elif fileparts_to_ignore == 'suffix':
        pattern_builder = remove_suffix
    else:
        MWRInputError("Known values for 'fileparts_to_ignore' are 'ext' and 'suffix' but found '{}'".
                      format(fileparts_to_ignore))

    files_sorted = sorted(files, key=pattern_builder)
    return [list(file_group) for _, file_group in groupby(files_sorted, key=pattern_builder)]


def remove_ext(file):
    """remove extension and just return pure filename including path"""
    return os.path.splitext(file)[0]


def remove_suffix(file, sep='_'):
    """remove suffix including extension (all that comes after last 'sep') and return pure filename including path"""
    fn_parts = remove_ext(file).split(sep)
    return sep.join(fn_parts[:-1])
