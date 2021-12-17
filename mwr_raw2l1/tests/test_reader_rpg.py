import unittest

import numpy as np

from mwr_raw2l1.readers.reader_rpg import BLB, BRT, HKD, IRT, MET
from mwr_raw2l1.utils.file_utils import abs_file_path, get_corresponding_pickle

PATH_DATA = 'mwr_raw2l1/tests/data/rpg/'


class TestReader(unittest.TestCase):
    """integration tests for rpg_reader.py"""

    def test_read_brt(self):
        filenames = ['C00-V859_190803.BRT', 'C00-V859_190804.BRT']  # TODO: instead of C00-V859_190804 add files with other filecodes (structver)
        self.reader_call_series(BRT, filenames)

    def test_read_blb(self):
        filenames = ['C00-V859_190803.BLB']  # TODO: add files with other filecodes (structver)
        self.reader_call_series(BLB, filenames)

    def test_read_irt(self):
        filenames = ['C00-V859_190803.IRT']  # TODO: add files with other filecodes (structver)
        self.reader_call_series(IRT, filenames)

    def test_read_hkd(self):
        filenames = ['C00-V859_190803.HKD']  # TODO: add files with other filecodes (structver)
        self.reader_call_series(HKD, filenames)

    def test_read_met(self):
        filenames = ['C00-V859_190803.MET']  # TODO: add files with other filecodes (structver)
        self.reader_call_series(MET, filenames)

    def reader_call_series(self, reader, filenames):
        for filename in filenames:
            with self.subTest(filename=filename):
                infile = abs_file_path(PATH_DATA, filename)
                x = reader(infile)

                # check whether data are same as previously read with actual reader
                with self.subTest(ref_data='actual reader'):
                    ref = get_corresponding_pickle(filename, PATH_DATA, legacy_reader=False)
                    for var in ref:
                        if var == 'time':
                            pass  # TODO: find a way to intercompare time decoding
                        else:
                            np.testing.assert_almost_equal(x.data[var], ref[var])

                # check if key variables match the ones read with the legacy reader
                with self.subTest(ref_data='legacy reader'):
                    ref = get_corresponding_pickle(filename, PATH_DATA, legacy_reader=True)
                    pass  # TODO: implement custom checks for key variables of legacy reader


if __name__ == '__main__':
    unittest.main()
