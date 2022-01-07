from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.readers.reader_rpg import read_multiple_files as reader_rpg
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config
from mwr_raw2l1.utils.file_utils import get_files
from mwr_raw2l1.write_netcdf import write


def main():
    conf_inst = get_inst_config('config/config_0-20000-0-06610_A.yaml')
    conf_nc = get_nc_format_config('config/L1_format.yaml')

    files = get_files('data/rpg/', 'C00-V859')
    all_data = reader_rpg(files)
    meas = Measurement.from_rpg(all_data)
    meas.run()

    write(meas.data, 'maintest.nc', conf_nc, conf_inst)
    pass


if __name__ == '__main__':
    main()
