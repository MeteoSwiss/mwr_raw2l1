"""integration tests for read-in and writing for Attex files

Features tested:
- compare key data in generated NetCDF with reference NetCDF file (test without concat option)
- check exception is raised if no header is present in data file
- check exception is raised if no column header is present in data file
"""

import glob
import os
import unittest

import xarray as xr
import yaml

from mwr_raw2l1.errors import MissingHeader, MWRTestError, UnknownRecordType
from mwr_raw2l1.log import logger
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.config_utils import get_inst_config
from mwr_raw2l1.utils.file_utils import abs_file_path
from tests.helper_functions import add_suffix, make_test_config

# list of variables to ignore in each test (best practice: only use for updating tests, otherwise set in sub-tests)
VARS_TO_IGNORE_GLOBAL = []


# instrument config definition
orig_inst_conf_file = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-99999_A.yaml'))
test_inst_conf_file = str(abs_file_path('tests/config/config_0-20000-0-99999_A.yaml'))
test_inst_conf_dir = str(abs_file_path('tests/config/'))  # all .yaml files will be removed from this directory
path_data_files_in = str(abs_file_path('tests/data/attex/0-20000-0-99999/'))
path_data_files_out = str(abs_file_path('tests/data/output/'))  # all .nc files will be removed from this directory

# NetCDF format definition
nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')

# quality control definition
qc_config_file = abs_file_path('mwr_raw2l1/config/qc_config.yaml')

# reference output file to compare against
reference_output = str(
    abs_file_path('tests/data/attex/reference_output/MWR_1C01_0-20000-0-99999_A20211107.nc'))


class TestAttex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        """Set up test class by generating test configuration from sample file"""
        nc_files_in_outdir = glob.glob(os.path.join(path_data_files_out, '*.nc'))
        if nc_files_in_outdir:
            err_msg = ("path_data_files_out ('{}') already contains NetCDF files. Refuse to run tests with output to "
                       'this directory as all NetCDF files in this directory would be removed after each test. Verify '
                       'path_data_files_out and remove files manually if needed'.format(path_data_files_out))
            raise MWRTestError(err_msg)
        cls.conf_inst = make_test_config(orig_inst_conf_file, test_inst_conf_file,
                                         path_data_files_in, path_data_files_out)
        cls.ds_ref = xr.load_dataset(reference_output)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done. Remove all test configuration files"""
        files_to_remove = glob.glob(os.path.join(test_inst_conf_dir, '*.yaml'))
        for file in files_to_remove:
            os.remove(file)

    def tearDown(self):
        """Remove generated NetCDF file after each test by removing all .nc-files from path_data_files_out"""
        files_to_remove = glob.glob(os.path.join(path_data_files_out, '*.nc'))
        for file in files_to_remove:
            os.remove(file)

    # Tests
    # -----
    def test_all_obs_available(self):
        """Test main function runs ok when all input file types are available"""
        self.single_test_call_series()

    def test_missing_header(self):
        """Test that an exception is raised if no header is present in data file"""
        infile_path_here = os.path.join(path_data_files_in, 'missing_header/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_header')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path_here, path_data_files_out)

        with self.assertRaises(MissingHeader):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file)

    def test_missing_colheader(self):
        """Test that an exception is raised if no column header is present in data file"""
        infile_path_here = os.path.join(path_data_files_in, 'missing_colhead/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_colhead')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path_here, path_data_files_out)

        with self.assertRaises(MissingHeader):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file)

    def test_alternative_file_format(self):
        """Test main function runs ok for file with dateformat %d/%m/%Y %H:%M.%S and with substitute character at EOF"""
        infile_path_here = os.path.join(path_data_files_in, 'alternative_format/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_alternative_format')
        reference_output_here = str(
            abs_file_path('tests/data/attex/reference_output/MWR_1C01_0-20000-0-99999_A202209220000.nc'))
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path_here, path_data_files_out)

        self.single_test_call_series(inst_config_file=inst_conf_file_here, ref_file=reference_output_here)

    # Helper methods
    # --------------
    def single_test_call_series(self, vars_to_ignore=None, check_timeseries_length=True,
                                inst_config_file=test_inst_conf_file, ref_file=None):
        """All steps a normal test should run through, i.e. executing main and checking contents of output NetCDF"""

        if ref_file is None:
            ds_ref_here = self.ds_ref
        else:
            ds_ref_here = xr.load_dataset(ref_file)

        if vars_to_ignore is None:
            vars_to_ignore = []
        vars_to_ignore.extend(VARS_TO_IGNORE_GLOBAL)

        # subTest
        with self.subTest(operation='run_main'):
            """Run entire processing chain in main method (read-in > Measurement > write NetCDF)"""
            run(inst_config_file, nc_format_config_file, qc_config_file)
        with self.subTest(operation='load_ouptut_netcdf'):
            """Load output NetCDF file with xarray. Failed test might indicate a corrupt file"""
            files = glob.glob(os.path.join(path_data_files_out, '*.nc'))
            if len(files) != 1:
                MWRTestError("Expected to find 1 file in test output directory ('{}') after running main but found {}"
                             .format(path_data_files_out, len(files)))
            self.ds = xr.load_dataset(files[0])
        with self.subTest(operation='check_output_vars'):
            """compare variables with sample NetCDF file"""
            ds_ref_sel = ds_ref_here.sel(time=self.ds.time)  # only time period of ds_ref that has also data in ds
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
                self.assertEqual(len(self.ds.time), len(ds_ref_here.time))
        with self.subTest(operation='check_output_att'):
            """check global attributes of output correspond to instrument config and that key attrs are present"""
            for attname, attval in self.conf_inst['nc_attributes'].items():
                self.assertIn(attname, self.ds.attrs)
                self.assertEqual(attval, self.ds.attrs[attname])
            for attname in ['network_name', 'license', 'history']:
                self.assertIn(attname, self.ds.attrs)
            self.assertIn('raw2l1', self.ds.attrs['history'].lower())
