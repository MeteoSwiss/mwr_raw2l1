"""integration tests for read-in and writing for RPG files for

The following observation settings are tested:
- RPG HATPRO
- RPG HATPRO with single observation in scan file
- RPG TEMPRO
- RPG LHATPRO (including test for effect of 0 entries for channels_ok in inst config)

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

from mwr_raw2l1.errors import MissingDataSource, MWRTestError
from mwr_raw2l1.log import logger
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.file_utils import abs_file_path
from tests.helper_functions import make_test_config, check_outdir_empty

# list of variables to ignore in each test (best practice: only use for updating tests, otherwise set in sub-tests)
VARS_TO_IGNORE_GLOBAL = []

# INPUTS DEPENDENT ON TEST CLASS (instrument config and reference output)
# =======================================================================
# RPG HATPRO standard config (including concat)
orig_inst_conf_file_hatpro = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))  # Payerne
path_data_files_in_hatpro = str(abs_file_path('tests/data/rpg/0-20000-0-06610/'))
reference_output_hatpro = str(abs_file_path(
    'tests/data/rpg/reference_output/MWR_1C01_0-20000-0-06610_A201908040100.nc'))

# RPG HATPRO with one single observation in (BLB-) data file
orig_inst_conf_file_single_obs = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))  # std HATPRO
path_data_files_in_single_obs = str(abs_file_path('tests/data/rpg/0-20000-0-06610_single_obs/'))
reference_output_single_obs = str(abs_file_path(
    'tests/data/rpg/reference_output/MWR_1C01_0-20000-0-06610_A202305190603_single_obs.nc'))

# RPG TEMPRO
orig_inst_conf_file_tempro = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06620_A.yaml'))  # Grenchen
path_data_files_in_tempro = str(abs_file_path('tests/data/rpg/0-20000-0-06620/'))
reference_output_tempro = str(abs_file_path(
    'tests/data/rpg/reference_output/MWR_1C01_0-20000-0-06620_A202305182358.nc'))

# RPG LHATPRO
orig_inst_conf_file_lhatpro = str(abs_file_path('mwr_raw2l1/config/config_0-20008-0-IZO_A.yaml'))  # Izaña
path_data_files_in_lhatpro = str(abs_file_path('tests/data/rpg/0-20008-0-IZO/'))
reference_output_lhatpro = str(abs_file_path(
    'tests/data/rpg/reference_output/MWR_1C01_0-20008-0-IZO_A202303241200.nc'))


# INPUTS COMMON TO ALL TEST CLASSES (NetCDF format and QC config, output paths)
# =============================================================================
nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')
qc_config_file = abs_file_path('mwr_raw2l1/config/qc_config.yaml')
path_data_files_out = str(abs_file_path('tests/data/output/'))  # all nc files will be removed from this directory
path_test_inst_conf_file = str(abs_file_path('tests/config/'))  # path for config files potentially alteretd during test


class TestRPGHatpro(unittest.TestCase):
    """Run RPG tests for (HATPRO) standard data with checks for missing data files"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)

        orig_inst_conf_file_here = orig_inst_conf_file_hatpro
        cls.test_inst_conf_file = os.path.join(path_test_inst_conf_file, os.path.basename(orig_inst_conf_file_here))
        cls.conf_inst = make_test_config(orig_inst_conf_file_here, cls.test_inst_conf_file,
                                         path_data_files_in_hatpro, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output_hatpro)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done. Remove test configuration file"""
        os.remove(cls.test_inst_conf_file)

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
            run(self.test_inst_conf_file, nc_format_config_file, qc_config_file)

    @patch('mwr_raw2l1.main.get_files')
    def test_no_hkd(self, get_files_mock):
        """Test that an exception is raised if no HKD file present as this is required for each instrument"""
        get_files_mock.return_value = self.infiles_mock(['.HKD'])
        with self.assertRaises(MissingDataSource):
            run(self.test_inst_conf_file, nc_format_config_file, qc_config_file)

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
            run(self.test_inst_conf_file, nc_format_config_file, qc_config_file, concat=True)
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

        infiles_for_test = glob.glob(os.path.join(self.conf_inst['input_directory'],
                                                  self.conf_inst['base_filename_in'] + '*'))
        for file in infiles_for_test.copy():
            if os.path.splitext(file)[-1].upper() in ext_to_exclude:
                infiles_for_test.remove(file)

        return infiles_for_test


class TestRPGSingleObs(TestRPGHatpro):
    """Re-run RPG HATPRO tests for data with a single-observation in BLB file (an occur for rapid data submission)"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)

        orig_inst_conf_file_here = orig_inst_conf_file_single_obs
        cls.test_inst_conf_file = os.path.join(path_test_inst_conf_file, os.path.basename(orig_inst_conf_file_here))
        cls.conf_inst = make_test_config(orig_inst_conf_file_here, cls.test_inst_conf_file,
                                         path_data_files_in_single_obs, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output_single_obs)


class TestRPGTempro(TestRPGHatpro):
    """Run RPG tests for TEMPRO (only a V-band temperature receiver, no humidity receiver)"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)

        orig_inst_conf_file_here = orig_inst_conf_file_tempro
        cls.test_inst_conf_file = os.path.join(path_test_inst_conf_file, os.path.basename(orig_inst_conf_file_here))
        cls.conf_inst = make_test_config(orig_inst_conf_file_here, cls.test_inst_conf_file,
                                         path_data_files_in_tempro, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output_tempro)

    def test_no_brt(self):
        logger.info('will not execute tests for missing BRT because the TEMPRO under test (0-20000-0-06620_A) is not '
                    'scanning and hence does not produce BLB, i.e. no brightness temperatures would be available')
        pass


class TestRPGLhatpro(TestRPGHatpro):
    """Run RPG tests for LHATPRO (V-band and 6-channel G-band receiver) incl. check on channels_ok"""

    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        check_outdir_empty(path_data_files_out)

        orig_inst_conf_file_here = orig_inst_conf_file_lhatpro
        cls.test_inst_conf_file = os.path.join(path_test_inst_conf_file, os.path.basename(orig_inst_conf_file_here))
        cls.conf_inst = make_test_config(orig_inst_conf_file_here, cls.test_inst_conf_file,
                                         path_data_files_in_lhatpro, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output_lhatpro)
        if cls.conf_inst['channels_ok'] != [1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1]:
            err_msg = 'reference output was genereated with channels_ok = [1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1] ' \
                       + 'in instrument config file but found {} in {} now'.format(
                           cls.conf_inst['channels_ok'], orig_inst_conf_file_here)
            raise MWRTestError(err_msg)

    def test_no_brt(self):
        logger.info('will not execute tests for missing BRT because the LHATPRO under test (0-20008-0-IZO_A) is not '
                    'scanning and hence does not produce BLB, i.e. no brightness temperatures would be available')
        pass

    def test_no_irt(self):
        logger.info('will not execute tests for missing IRT because the LHATPRO under test (0-20008-0-IZO_A) has 2 IR '
                    'channels but if no IRT file is present and no specification is made in inst config file, one '
                    'single IR wavelength is assumed to set the dimensions in the output file what would trigger a '
                    'dimension mismatch with the reference output file.')
        pass
