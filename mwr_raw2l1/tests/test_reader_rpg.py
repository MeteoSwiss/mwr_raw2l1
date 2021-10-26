from unittest import TestCase

from mwr_raw2l1.reader_rpg import BRT, BLB, IRT, MET, HKD
from mwr_raw2l1.utils.file_utils import abs_file_path

PATH_DATA = 'mwr_raw2l1/tests/data/rpg/'


class TestReader(TestCase):

    def test_read_brt(self):
        filenames = ['C00-V859_190803.BRT', 'C00-V859_190804.BRT']  # TODO: instead of C00-V859_190804 add files with other filecodes (structver)
        self.reader_call_series(BRT, filenames)

    def test_read_blb(self):
        filenames = ['C00-V859_190803.BLB', ]  # TODO: add files with other filecodes (structver)
        self.reader_call_series(BLB, filenames)

    def test_read_irt(self):
        filenames = ['C00-V859_190803.IRT', ]  # TODO: add files with other filecodes (structver)
        self.reader_call_series(IRT, filenames)

    def test_read_hkd(self):
        filenames = ['C00-V859_190803.HKD', ]  # TODO: add files with other filecodes (structver)
        self.reader_call_series(HKD, filenames)

    def test_read_met(self):
        filenames = ['C00-V859_190803.MET', ]  # TODO: add files with other filecodes (structver)
        self.reader_call_series(MET, filenames)

    def reader_call_series(self, reader, filenames):
        for filename in filenames:
            with self.subTest(filename=filename):
                infile = abs_file_path(PATH_DATA, filename)
                reader(infile)
