from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.readers.reader_rpg import read_multiple_files as read_rpg
from mwr_raw2l1.utils.file_utils import get_files
from mwr_raw2l1.write_netcdf import write


def main():
    files = get_files('data/rpg/', 'C00-V859')
    all_data = read_rpg(files)
    meas = Measurement.from_rpg(all_data)
    meas.run()

    write(meas.data, 'maintest.nc', 'config/L1_format.yaml', 'config/config_0-20000-0-06610_A.yaml')
    pass


if __name__ == '__main__':
    main()
