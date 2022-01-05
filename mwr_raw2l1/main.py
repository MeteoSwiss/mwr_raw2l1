from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.readers.reader_rpg import read_all as read_rpg
from mwr_raw2l1.write_netcdf import write

all_data = read_rpg('data/rpg/', 'C00-V859')
meas = Measurement.from_rpg(all_data)
meas.run()

write(meas.data, 'maintest.nc', 'config/L1_format.yaml', 'config/config_0-20000-0-06610_A.yaml')
pass
