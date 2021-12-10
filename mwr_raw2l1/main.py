from mwr_raw2l1.measurement import Measurement
from mwr_raw2l1.readers.reader_rpg import read_all as read_rpg
from mwr_raw2l1.write_netcdf import write

all_data = read_rpg('data/rpg/', 'C00-V859')
meas = Measurement.from_rpg(all_data)
# TODO: either transform whole xarray dataset or just transform time
# dummy = xr.Dataset.to_dict(meas.data)
# data_simple = {}
# for
write(meas.data, 'maintest.nc', 'config/L1_format.yaml')
pass
