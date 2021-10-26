from pathlib import Path

import mwr_raw2l1


def abs_file_path(*file_path):
    """
    Make a relative file_path absolute in respect to the mwr_raw2l1 project directory.
    Absolute path wil not be changed
    """
    path = Path(*file_path)
    if path.is_absolute():
        return path
    return Path(mwr_raw2l1.__file__).parent.parent / path


def get_binary(filename):
    """return the entire content of the binary file as binary stream"""
    with open(filename, 'rb') as f:
        return f.read()