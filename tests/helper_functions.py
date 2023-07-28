import glob
import os

import yaml

from mwr_raw2l1.errors import MWRTestError
from mwr_raw2l1.utils.config_utils import get_inst_config


def make_test_config(orig_config_file, test_config_file, path_data_in, path_data_out):
    """get sample config file and modify and save as test config file and return test config dictionary

    Args:
        orig_config_file: path to sample config file
        test_config_file: path where to store modified config file for testing. If None, config is returned but not
            written to any file
        path_data_in: path where to look for input observation files for testing
        path_data_out: path where to store output file during testing
    Returns:
        configuration dict of test config
    """
    conf_inst = get_inst_config(orig_config_file)
    conf_inst['input_directory'] = path_data_in
    conf_inst['output_directory'] = path_data_out
    if test_config_file is not None:
        with open(test_config_file, 'w') as f:
            yaml.dump(conf_inst, f)
    return conf_inst


def check_outdir_empty(path_files_out, search_pattern='*.nc'):
    """check that no files matching search pattern are found in path_files_out"""
    nc_files_in_outdir = glob.glob(os.path.join(path_files_out, search_pattern))
    if nc_files_in_outdir:
        err_msg = ("path_data_files_out ('{}') already contains NetCDF files. Refuse to run tests with output to "
                   'this directory as all NetCDF files in this directory would be removed after each test. Verify '
                   'path_data_files_out and remove files manually if needed'.format(path_files_out))
        raise MWRTestError(err_msg)


def add_suffix(filename, suffix):
    """add suffix to the end of filename, but before the extenxion"""
    fn_split = os.path.splitext(filename)
    return fn_split[0] + suffix + fn_split[1]
