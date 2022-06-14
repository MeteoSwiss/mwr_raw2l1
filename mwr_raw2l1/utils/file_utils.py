import glob
import os
import pickle
from itertools import groupby
from pathlib import Path

import mwr_raw2l1
from mwr_raw2l1.errors import FilenameError, MWRInputError


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

    If 'time_start' and/or 'time_end' is given only files with timestamp in filename >='time_start' and/or <='time_end'
    are returned. E.g. time_start=20220101 and time_end=20220101 will return timestamps 20220101 and 202201010000.

    Args:
        dir_in: directory where files of the respective instrument are located
        basename: first part of the filename (usually full identifier combining station-id and instrument-id)
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
        try:
            fn_date = datestr_from_filename(file)
        except FilenameError:
            files.remove(file)
            mwr_raw2l1.log.logger.warning("Cannot process '{}' as filename doesn't match expected pattern".format(file))
        if time_start is not None:
            if timestamp_to_float(fn_date) < timestamp_to_float(time_start):
                files.remove(file)
                continue
        if time_end is not None:
            if timestamp_to_float(fn_date) > timestamp_to_float(time_end):
                files.remove(file)
                continue

    return files


def datestr_from_filename(filename):
    """return date string from filename, assuming it to be the last block (separated by _)  of minimum 4 decimal digits

    Accepted dates are in form 'yyyymmddHHMM', 'yyyymmddHHMMSS', 'yyyymmdd', 'yymm' etc. but not separated by -, _ or :

    Args:
        filename: filename as str. Can contain path and extension.
    Returns:
        string containing the date in same representation as in the filename
    """
    min_date_length = 4
    fn_parts = os.path.splitext(filename)[0].split('_')
    for block in reversed(fn_parts):  # try to find date str parts of filename, starting at the end
        if len(block) < min_date_length:
            continue
        if block.isdecimal():
            return block
        if block[1:].isdecimal() and len(block)-1 >= min_date_length:  # block has ID at start, e.g. _A202206010000
            return block[1:]
    raise FilenameError("found no date in '{}'".format(filename))


def timestamp_to_float(timestamp):
    """transform timestamp string to a float between 0 and 1 (integer of timestamp normalised by its length)"""
    return int(timestamp)/10**len(timestamp)


def generate_output_filename(basename, timestamp_src, files_in=None, time=None, ext='nc'):
    """generate filename in form {basename}{timestamp}.{ext} where timestamp comes from input files or time vector

    Args:
        basename: the first part of the filename without the date
        timestamp_src: source of output file timestamp.
            Can be 'instamp_min'/'instamp_max' for using smallest/largest timestamp of input filenames (needs 'files_in)
            or 'time_min'/'time_max' for smallest/largest time in data in format yyyymmddHHMM (needs 'time').
        files_in: list of input filenames to processing as a basis for timestamp selection
        time: :class:`xarray.DataArray` time vector of the data in :class:`numpy.datetime64` format. Assume to be sorted
        ext (optional): filename extension. Defaults to 'nc'. Empty not permitted.
    """
    format_stamp = '%Y%m%d%H%M'  # only used for timestamp_src='time_min' or 'time_max'

    # handle input
    if timestamp_src in ['instamp_min', 'instamp_max']:
        if files_in is None:
            raise MWRInputError("if timestamp_src is 'instamp_min' or 'instamp_max' input 'files_in' must be given")
        timestamps = sorted([datestr_from_filename(f) for f in files_in], key=timestamp_to_float)
    elif timestamp_src in ['time_min', 'time_max']:
        if time is None:
            raise MWRInputError("if timestamp_src is 'time_min' or 'time_max' input 'time' must be given")

    # produce output timestamp
    if timestamp_src == 'instamp_min':
        timestamp = timestamps[0]
    elif timestamp_src == 'instamp_max':
        timestamp = timestamps[-1]
    elif timestamp_src == 'time_min':
        timestamp = time[0].dt.strftime(format_stamp).data
    elif timestamp_src == 'time_max':
        timestamp = time[-1].dt.strftime(format_stamp).data
    else:
        raise MWRInputError("Known values for 'timestamp_src' are {} but found '{}'".format(
            "['instamp_min', 'instamp_max', 'time_min', 'time_max']", timestamp_src))

    return '{}{}.{}'.format(basename, timestamp, ext)


def group_files(files, name_scheme):
    """group files in a list of files

    Args:
        files: list of files
        name_scheme ({'attex', 'rpg', 'radiometrics'}): scheme of filename used for parts to ignore in grouping process
    Returns:
        list of lists of files for which all parts except the ignored ones are identical
    """
    if name_scheme in ['attex', 'rpg']:
        pattern_builder = remove_ext
    elif name_scheme == 'radiometrics':
        pattern_builder = remove_suffix
    else:
        MWRInputError("known values for 'name_scheme' are 'attex', 'radiometrics' and 'rpg' but found '{}'".
                      format(name_scheme))

    files_sorted = sorted(files, key=pattern_builder)
    return [list(file_group) for _, file_group in groupby(files_sorted, key=pattern_builder)]


def remove_ext(file):
    """remove extension and just return pure filename including path"""
    return os.path.splitext(file)[0]


def remove_suffix(file, sep='_'):
    """remove suffix including extension (all that comes after last 'sep') and return pure filename including path"""
    fn_parts = remove_ext(file).split(sep)
    return sep.join(fn_parts[:-1])


def write_file_log(outfile, file_bunches):
    """write bunches of (un)successfully processed files to an output file.

    Stores each path on one line with empty line between bunches.

    Args:
        outfile: file where to write in (will be generated/overwritten)
        file_bunches: list of file bunches i.e. a list of lists of files
    """
    with open(outfile, 'w') as f:
        for bunch in file_bunches:
            for file in bunch:
                f.write('{}\n'.format(file))
            f.write('\n')  # separate bunches by an empty line


if __name__ == '__main__':
    fn = generate_output_filename('asfd', 'instamp_max', files_in=['lkja_q20220102', 'asdfa_202201020001', 'lkjlj_20220103'])
    print(fn)
    pass
