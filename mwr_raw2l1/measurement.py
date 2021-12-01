import xarray as xr

from mwr_raw2l1.measurement_helpers import make_dataset


class Measurement(object):
    def __init__(self):
        self.data = None

    @classmethod
    def from_rpg(cls, readin_data):
        """constructor for data read in from RPG instruments.

        Args:
            readin_data: dictionary with list of instances for each RPG read-in class (keys correspond to filetype)
        """
        # dimensions and variable names for usage with make_dataset
        dims = {'brt': ['time', 'frequency'],
                'blb': ['time', 'frequency', 'scan_ele'],
                'irt': ['time', 'wavelength'],
                'met': ['time'],
                'hkd': ['time']}
        vars = {'brt': ['Tb', 'rainflag', 'ele', 'azi'],
                'blb': ['Tb_scan', 'T_per_scan', 'rainflag', 'scan_quadrant'],
                'irt': ['IRT', 'rainflag', 'ele', 'azi'],
                'met': ['p', 'T', 'RH'],
                'hkd': ['alarm']}
        vars_opt = {'brt': [],
                    'blb': [],
                    'irt': [],
                    'met': ['windspeed', 'winddir', 'rainrate'],
                    'hkd': ['lat', 'lon', 'T_amb_1', 'T_amb_2', 'T_receiver_kband', 'T_receiver_vband',
                            'Tstab_kband', 'Tstab_vband', 'flashmemory_remaining', 'statusflag']}

        out = cls
        all_data = {}
        for ext, data_series in readin_data.items():
            data_act = []
            for dat in data_series:  # make an xarray dataset from the data dict in each class instance
                data_act.append(make_dataset(dat.data, dims[ext], vars[ext], vars_opt[ext]))
            all_data[ext] = xr.concat(data_act, dim='time')  # merge all datasets of the same type

        out.data = all_data['brt']  # TODO: merge BRT and BLB (use HKD for evaluating scan time) & interpolate irt, met, hkd
        # TODO: ask Volker where to do transformation from BLB scan to timeseries. probably here as use HKD info. But it is still a very BLB-specific method
        return out

    # TODO: Example code, remove when done
    @classmethod
    def from_signal(cls, signal_a, signal_b):
        result = cls()
        result.combine(signal_a, signal_b)
        return result

    def combine(self, signal_a, signal_b):
        self.data = signal_b + signal_a
        pass

    # TODO: use 3 different class methods to read in data from the different instruments to a common measurement class
    # don't need a BaseMeasurement class in this case as only 1. Measurement class can then be handed over to writer

    # TODO: for combining to time series use xarray dataset. For writing, might maybe still use netCDF4


if __name__ == '__main__':
    from mwr_raw2l1.reader_rpg import read_all

    all_data = read_all('data/rpg/', 'C00-V859')
    meas = Measurement.from_rpg(all_data)
    pass
