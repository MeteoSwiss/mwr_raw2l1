"""integration tests for read-in and writing for RPG files

Features tested:
- run main and compare key data in generated NetCDF with reference NetCDF file (test with concat option)
- check run for missing brt or blb file
- check run for missing irt file
- check run for missing met file
- check exception is raised if no brightness temperature files are available (brt or blb)
- check exception is raised if no housekeeping data (hkd) file is available
"""

import glob
import os
import unittest
from unittest.mock import patch

import xarray as xr
import yaml

from mwr_raw2l1.errors import MissingDataSource, MWRTestError
from mwr_raw2l1.log import logger
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.config_utils import get_inst_config
from mwr_raw2l1.utils.file_utils import abs_file_path

# list of variables to ignore in each test (best practice: only use for updating tests, otherwise set in sub-tests)
VARS_TO_IGNORE_GLOBAL = []


# instrument config definition
orig_inst_conf_file = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
test_inst_conf_file = str(abs_file_path('tests/config/config_0-20000-0-06610_A.yaml'))
path_data_files_in = str(abs_file_path('tests/data/rpg/0-20000-0-06610/'))
path_data_files_in_single_obs = str(abs_file_path('tests/data/rpg/0-20000-0-06610_single_obs/'))
path_data_files_out = str(abs_file_path('tests/data/output/'))  # all nc files will be removed from this directory

# NetCDF format definition
nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')

# quality control definition
qc_config_file = abs_file_path('mwr_raw2l1/config/qc_config.yaml')

# reference output file to compare against
reference_output = str(abs_file_path('tests/data/rpg/reference_output/MWR_1C01_0-20000-0-06610_A201908040100.nc'))
reference_output_single_obs = str(abs_file_path(
    'tests/data/rpg/reference_output/MWR_1C01_0-20000-0-06610_A202305190603_single_obs.nc'))


class TestRPG(unittest.TestCase):
    """Run RPG tests for standard data with checks for missing data files"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)
        cls.path_data_files_in = path_data_files_in
        cls.conf_inst = make_test_config(orig_inst_conf_file, test_inst_conf_file,
                                         cls.path_data_files_in, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output)

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
        self.single_test_call_series()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_irt(self, get_files_mock):
        """Test main function runs ok when IRT files are missing"""
        vars_to_ignore = ['irt', 'ir_wavelength', 'ir_azi', 'ir_ele']
        get_files_mock.return_value = self.infiles_mock(['.IRT'])
        self.single_test_call_series(vars_to_ignore)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_met(self, get_files_mock):
        """Test main function runs ok when MET files are missing"""
        vars_to_ignore = ['air_pressure', 'air_temperature', 'relative_humidity',
                          'wind_speed', 'wind_direction', 'rain_rate']
        get_files_mock.return_value = self.infiles_mock(['.MET'])
        self.single_test_call_series(vars_to_ignore)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_brt(self, get_files_mock):
        """Test main function runs ok when BRT files are missing"""
        vars_to_ignore = ['azi', 'quality_flag', 'quality_flag_status']  # azi not encoded in BLB, sun flag needs azi
        get_files_mock.return_value = self.infiles_mock(['.BRT'])
        self.single_test_call_series(vars_to_ignore, check_timeseries_length=False)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_blb(self, get_files_mock):
        """Test main function runs ok when BLB files are missing"""
        get_files_mock.return_value = self.infiles_mock(['.BLB'])
        self.single_test_call_series(check_timeseries_length=False)
        get_files_mock.assert_called()

    @patch('mwr_raw2l1.main.get_files')
    def test_no_brt_no_blb(self, get_files_mock):
        """Test that an exception is raised if neither of blb or brt files are present (at least on Tb obs required)"""
        get_files_mock.return_value = self.infiles_mock(['.BRT', '.BLB'])
        with self.assertRaises(MissingDataSource):
            run(test_inst_conf_file, nc_format_config_file, qc_config_file)

    @patch('mwr_raw2l1.main.get_files')
    def test_no_hkd(self, get_files_mock):
        """Test that an exception is raised if no HKD file present as this is required for each instrument"""
        get_files_mock.return_value = self.infiles_mock(['.HKD'])
        with self.assertRaises(MissingDataSource):
            run(test_inst_conf_file, nc_format_config_file, qc_config_file)

    # Helper methods
    # --------------
    def single_test_call_series(self, vars_to_ignore=None, check_timeseries_length=True):
        """All steps a normal test should run through, i.e. executing main and checking contents of output NetCDF"""

        if vars_to_ignore is None:
            vars_to_ignore = []
        vars_to_ignore.extend(VARS_TO_IGNORE_GLOBAL)

        # subTest
        with self.subTest(operation='run_main'):
            """Run entire processing chain in main method (read-in > Measurement > write NetCDF)"""
            run(test_inst_conf_file, nc_format_config_file, qc_config_file, concat=True)
        with self.subTest(operation='load_ouptut_netcdf'):
            """Load output NetCDF file with xarray. Failed test might indicate a corrupt file"""
            files = glob.glob(os.path.join(path_data_files_out, '*.nc'))
            if len(files) != 1:
                MWRTestError("Expected to find 1 file in test output directory ('{}') after running main but found {}"
                             .format(path_data_files_out, len(files)))
            self.ds = xr.load_dataset(files[0])
        with self.subTest(operation='check_output_vars'):
            """compare variables with sample NetCDF file"""
            ds_ref_sel = self.ds_ref.sel(time=self.ds.time)  # only time period of ds_ref that has also data in ds
            ds_ref_sel = ds_ref_sel.drop_vars(vars_to_ignore, errors='ignore')  # no error if var to ignore is missing
            ds_sel = self.ds.drop_vars(vars_to_ignore, errors='ignore')
            vars_not_in_ref = [var for var in list(ds_sel.keys()) if var not in list(ds_ref_sel.keys())]
            if vars_not_in_ref:
                logger.warning('The following variables cannot be tested as they are not in the reference dataset: {}'
                               .format(vars_not_in_ref))
                ds_sel = ds_sel.drop_vars(vars_not_in_ref)
            xr.testing.assert_allclose(ds_sel, ds_ref_sel)
        if check_timeseries_length:
            with self.subTest(operation='check_whole_timeseries_in_nc'):
                """compare length of time vector with reference. Not detected due to selection in check_output_vars"""
                self.assertEqual(len(self.ds.time), len(self.ds_ref.time))
        with self.subTest(operation='check_output_att'):
            """check global attributes of output correspond to instrument config and that key attrs are present"""
            for attname, attval in self.conf_inst['nc_attributes'].items():
                self.assertIn(attname, self.ds.attrs)
                self.assertEqual(attval, self.ds.attrs[attname])
            for attname in ['network_name', 'license', 'history']:
                self.assertIn(attname, self.ds.attrs)
            self.assertIn('raw2l1', self.ds.attrs['history'].lower())

    def infiles_mock(self, ext_to_exclude):
        """Mock for return value of get_files

         Args:
             ext_to_exclude: list of extensions to exclude from file list. Extensions must contain dot as first digit'
         Returns:
            all files in self.path_data_in except the ones with an extension specified in ext_to_exclude
        """
        infiles_for_test = glob.glob(os.path.join(self.path_data_files_in, self.conf_inst['base_filename_in'] + '*'))
        for file in infiles_for_test.copy():
            if os.path.splitext(file)[-1].upper() in ext_to_exclude:
                infiles_for_test.remove(file)
        return infiles_for_test


class TestRPGSingleObs(TestRPG):
    """Re-run RPG tests but for data with a single-observation in BLB file"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)
        cls.path_data_files_in = path_data_files_in_single_obs
        cls.conf_inst = make_test_config(orig_inst_conf_file, test_inst_conf_file,
                                         cls.path_data_files_in, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output_single_obs)


def make_test_config(orig_config_file, test_config_file, path_data_in, path_data_out):
    """get sample config file and modify and save as test config file and return test config dictionary

    Args:
        orig_config_file: path to sample config file
        test_config_file: path where to store modified config file for testing
        path_data_in: path where to look for input observation files for testing
        path_data_out: path where to store output file during testing
    Returns:
        configuration dict of test config
    """
    conf_inst = get_inst_config(orig_config_file)
    conf_inst['input_directory'] = path_data_in
    conf_inst['output_directory'] = path_data_out
    f = open(test_config_file, 'w')  # with open... does not work here for some reason
    yaml.dump(conf_inst, f)
    f.close()
    return conf_inst


def check_outdir_empty(path_files_out, search_pattern='*.nc'):
    """check that no files matching search pattern are found in path_files_out"""
    nc_files_in_outdir = glob.glob(os.path.join(path_files_out, search_pattern))
    if nc_files_in_outdir:
        err_msg = ("path_data_files_out ('{}') already contains NetCDF files. Refuse to run tests with output to "
                   'this directory as all NetCDF files in this directory would be removed after each test. Verify '
                   'path_data_files_out and remove files manually if needed'.format(path_files_out))
        raise MWRTestError(err_msg)
