"""integration tests for read-in and writing for Radiometrics files

Features tested:
- run main and compare key data in generated NetCDF with reference NetCDF file
- check main runs error-free for extra line (to be ignored) after header in data file
- check exception is raised if no header is present in data file
- check exception is raised if data file does not contain column header info for one record type in the data file
"""

import glob
import os
import unittest

import xarray as xr
import yaml

from mwr_raw2l1.errors import CorruptRectype, MissingData, MissingHeader, MWRTestError, UnknownRecordType
from mwr_raw2l1.log import logger
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.config_utils import get_inst_config
from mwr_raw2l1.utils.file_utils import abs_file_path

# list of variables to ignore in each test (best practice: only use for updating tests, otherwise set in sub-tests)
VARS_TO_IGNORE_GLOBAL = []


# instrument config definition
orig_inst_conf_file = str(abs_file_path('mwr_raw2l1/config/config_0-20000-0-10393_A.yaml'))
test_inst_conf_file = str(abs_file_path('tests/config/config_0-20000-0-10393_A.yaml'))
test_inst_conf_dir = str(abs_file_path('tests/config/'))  # all .yaml files will be removed from this directory
path_data_files_in = str(abs_file_path('tests/data/radiometrics/0-20000-0-10393/'))
path_data_files_out = str(abs_file_path('tests/data/output/'))  # all .nc files will be removed from this directory

# NetCDF format definition
nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')

# quality control definition
qc_config_file = abs_file_path('mwr_raw2l1/config/qc_config.yaml')

# reference output file to compare against
reference_output = str(
    abs_file_path('tests/data/radiometrics/reference_output/MWR_1C01_0-20000-0-10393_A202101310004.nc'))


class TestRadiometrics(unittest.TestCase):
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

    def test_extra_headerline(self):
        """Test main function runs through when data file has an extra headerline (saw this for some DWD files)"""
        # no need to test again that values are seen ok, just see that main method runs without errors
        infile_path_here = os.path.join(path_data_files_in, 'missing_headerline/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_headerline')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

    def test_empty_lines(self):
        """Test main function runs through when data file contains extra empty lines"""
        # no need to test again that values are seen ok, just see that main method runs without errors
        infile_path_here = os.path.join(path_data_files_in, 'empty_lines/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_empty_lines')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

    def test_missing_header(self):
        """Test that an exception is raised if no header is present in data file (saw this for some DWD files)"""
        infile_path_here = os.path.join(path_data_files_in, 'missing_header/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_header')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        with self.assertRaises(MissingHeader):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

    def test_missing_colhead(self):
        """Test that an exception is raised if no column header to data record type present in data file"""
        infile_path_here = os.path.join(path_data_files_in, 'missing_colhead/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_colhead')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        with self.assertRaises(UnknownRecordType):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

    def test_missing_data(self):
        """Test that an exception is raised if file contains no data section"""
        infile_path_here = os.path.join(path_data_files_in, 'missing_data/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_missing_data')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        with self.assertRaises(MissingData):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

    def test_corrupt_rectype(self):
        """Test that an exception is raised if file is corrupt and record type cannot be converted to int"""
        infile_path_here = os.path.join(path_data_files_in, 'corrupt_rectype/')
        inst_conf_file_here = add_suffix(test_inst_conf_file, '_corrupt_rectype')
        make_test_config(test_inst_conf_file, inst_conf_file_here, infile_path=infile_path_here)

        with self.assertRaises(CorruptRectype):
            run(inst_conf_file_here, nc_format_config_file, qc_config_file, concat=True)

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


def make_test_config(orig_config_file, test_config_file=None, infile_path=path_data_files_in):
    """get sample config file and modify and save as test config file and return test config dictionary

    Args:
        orig_config_file: path to sample config file
        test_config_file: path where to store modified config file for testing. If None, config is returned but not
            written to any file
        infile_path: path of input data files to read. Default is path_data_files_in defined globally.
    Returns:
        configuration dict of test config
    """
    conf_inst = get_inst_config(orig_config_file)
    conf_inst['input_directory'] = infile_path
    conf_inst['output_directory'] = path_data_files_out
    if test_config_file is not None:
        f = open(test_config_file, 'w')  # with open... does not work here for some reason
        yaml.dump(conf_inst, f)
        f.close()
    return conf_inst


def add_suffix(filename, suffix):
    """add suffix to the end of filename, but before the extenxion"""
    fn_split = os.path.splitext(filename)
    return fn_split[0] + suffix + fn_split[1]
