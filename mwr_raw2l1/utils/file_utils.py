from pathlib import Path
import pickle
import os

import yaml

import mwr_raw2l1


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


def get_conf(file):
    with open(file) as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf