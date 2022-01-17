"""integration tests for read-in and writing for RPG files"""


# - compare key data in generated NetCDF with reference NetCDF file
# - check run for missing brt or blb file
# - check run for missing irt file
# - check run for missing met file
#
# - additionally test if all works when removing BL_scan active from HKD
import glob
import os
import unittest
from unittest.mock import patch

import yaml

from mwr_raw2l1.errors import MissingDataSource, MWRTestError
from mwr_raw2l1.main import main
from mwr_raw2l1.utils.config_utils import get_inst_config
from mwr_raw2l1.utils.file_utils import abs_file_path

# instrument config definition
orig_inst_conf_file = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
test_inst_conf_file = str(abs_file_path('tests/config/config_0-20000-0-06610_A.yaml'))
path_data_files_in = str(abs_file_path('tests/data/rpg/0-20000-0-06610/'))
path_data_files_out = str(abs_file_path('tests/data/output/'))  # all nc files will be removed from this directory

# NetCDF format definition
nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')


class TestRPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        nc_files_in_outdir = glob.glob(os.path.join(path_data_files_out, '*.nc'))
        if nc_files_in_outdir:
            err_msg = ("path_data_files_out ('{}') already contains NetCDF files. Refuse to run tests with output to "
                       'this directory as all NetCDF files in this directory would be removed after each test. Verify '
                       'path_data_files_out and remove files manually if needed'.format(path_data_files_out))
            raise MWRTestError(err_msg)
        cls.conf_inst = make_test_config(orig_inst_conf_file, test_inst_conf_file)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done. Remove test configuration file"""
        os.remove(test_inst_conf_file)

    def tearDown(self):
        """Remove generated NetCDF file after each test by removing all .nc-files from path_data_files_out"""
        files_to_remove = glob.glob(os.path.join(path_data_files_out, '*.nc'))
        for file in files_to_remove:
            os.remove(file)

    # Tests
    # -----
    def test_all_infiles_available(self):
        """Test main function runs ok when all input file types are available"""
        vars_to_test = ['tb']  # variable names according to NetCDF file standard
        atrrs_to_test = ['network']

        self.single_test_call_series(vars_to_test, atrrs_to_test)

    @patch('mwr_raw2l1.main.get_files')
    def test_no_irt(self, get_files_mock):
        """Test main function runs ok when IRT files are missing"""
        vars_to_test = ['tb']
        atrrs_to_test = ['network']

        get_files_mock.return_value = self.infiles_mock(['.IRT'])
        self.single_test_call_series(vars_to_test, atrrs_to_test)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_met(self, get_files_mock):
        """Test main function runs ok when MET files are missing"""
        vars_to_test = ['tb']
        atrrs_to_test = ['network']

        get_files_mock.return_value = self.infiles_mock(['.MET'])
        self.single_test_call_series(vars_to_test, atrrs_to_test)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_brt(self, get_files_mock):
        """Test main function runs ok when BRT files are missing"""
        vars_to_test = ['tb']
        atrrs_to_test = ['network']

        get_files_mock.return_value = self.infiles_mock(['.BRT'])
        self.single_test_call_series(vars_to_test, atrrs_to_test, check_timeseries_length=False)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_blb(self, get_files_mock):
        """Test main function runs ok when BLB files are missing"""
        vars_to_test = ['tb']
        atrrs_to_test = ['network']

        get_files_mock.return_value = self.infiles_mock(['.BLB'])
        self.single_test_call_series(vars_to_test, atrrs_to_test, check_timeseries_length=False)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_brt_no_blb(self, get_files_mock):
        """Test that an exception is raised if neither of blb or brt files are present (at least on Tb obs required)"""
        get_files_mock.return_value = self.infiles_mock(['.BRT', '.BLB'])
        with self.assertRaises(MissingDataSource):
            main(test_inst_conf_file, nc_format_config_file)

    @patch('mwr_raw2l1.main.get_files')
    def test_no_hkd(self, get_files_mock):
        """Test that an exception is raised if no HKD file present as this is required for each instrument"""
        get_files_mock.return_value = self.infiles_mock(['.HKD'])
        with self.assertRaises(MissingDataSource):
            main(test_inst_conf_file, nc_format_config_file)

    # Helper methods
    # --------------
    def single_test_call_series(self, vars_to_test, atrrs_to_test, check_timeseries_length=True):
        """all steps a normal test should run through, i.e. executing main and checking contents of output NetCDF"""
        with self.subTest(operation='run_main'):
            main(test_inst_conf_file, nc_format_config_file)
        with self.subTest(operation='check_output_vars'):
            """compare variable values with sample NetCDF file"""
            pass
        with self.subTest(operation='check_output_att'):
            """compare global attributes with sample NetCDF file"""
            pass
        if check_timeseries_length:
            with self.subTest(operation='check_whole_timeseries_in_nc'):
                pass

    def infiles_mock(self, ext_to_exclude):
        """Mock for return value of get_files

         Args:
             ext_to_exclude: list of extensions to exclude from file list. Extensions must contain dot as first digit'
         Returns:
            all files in path_data_files_in except the ones with an extension specified in ext_to_exclude
        """
        infiles_for_test = glob.glob(os.path.join(path_data_files_in, self.conf_inst['base_filename_in'] + '*'))
        for file in infiles_for_test.copy():
            if os.path.splitext(file)[-1].upper() in ext_to_exclude:
                infiles_for_test.remove(file)
        return infiles_for_test


def make_test_config(orig_config_file, test_config_file):
    """get sample config file and modify and save as test config file and return test config dictionary

    Args:
        orig_config_file: path to sample config file
        test_config_file: path where to store modified config file for testing
    Returns:
        configuration dict of test config
    """
    conf_inst = get_inst_config(orig_config_file)
    conf_inst['input_directory'] = path_data_files_in
    conf_inst['output_directory'] = path_data_files_out
    f = open(test_config_file, 'w')  # with open... does not work here for some reason
    yaml.dump(conf_inst, f)
    f.close()
    return conf_inst
