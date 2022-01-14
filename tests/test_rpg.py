"""integration tests for read-in and writing for RPG files"""


# - compare key data in generated NetCDF with reference NetCDF file
# - check run for missing brt or blb file
# - check run for missing irt file
# - check run for missing met file
#
# - additionally test if all works when removing BL_scan active from HKD
import os
import unittest

import yaml

from mwr_raw2l1.utils.config_utils import get_inst_config
from mwr_raw2l1.utils.file_utils import abs_file_path

orig_inst_conf_file = abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml')
test_inst_conf_file = abs_file_path('tests/config/config_0-20000-0-06610_A.yaml')
path_data_files_in = abs_file_path('tests/data/rpg/0-20000-0-06610/')
path_data_files_out = abs_file_path('tests/data/output/')


class TestRPG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):  # this is only executed once at init of class
        make_test_config(orig_inst_conf_file, test_inst_conf_file)

    @classmethod
    def tearDownClass(cls):
        os.remove(test_inst_conf_file)

    def tearDown(self):
        pass
        # TODO: remove produced output NetCDF file

    def test_main(self):
        pass
        # TODO: use self.subTest for full file availabilty and absence of input (brt, blb, hkd)


def make_test_config(orig_config_file, test_config_file):
    conf_inst = get_inst_config(orig_config_file)
    conf_inst['input_directory'] = path_data_files_in
    conf_inst['output_directory'] = path_data_files_out
    f = open(test_config_file, 'w')  # with open... does not work here for some reason
    yaml.dump(conf_inst, f)
    f.close()
