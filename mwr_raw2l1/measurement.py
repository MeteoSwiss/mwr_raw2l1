import xarray as xr


class Measurement(object):
    def __init__(self):
        self.data = None

    @classmethod
    def from_rpg(cls, readin_data):
        """constructor for data read in from RPG instruments.

        Args:
            readin_data: dictionary with list of instances for each RPG read-in class (keys correspond to filetype)
        """
        # dimensions and variable names for usage with make_xr_dict
        dims = {'brt': ['time', 'frequency'],
                'blb': ['time', 'frequency', 'ele'],
                'irt': ['time', 'wavelength'],
                'met': 'time',
                'hkd': 'time'}
        vars = {'brt': ['Tb', 'rainflag', 'ele', 'azi'],
                'blb': ['Tb_scan', 'T_per_scan', 'rainflag', 'scan_quadrant', 'ele'],
                'irt': ['IRT', 'rainflag', 'ele', 'azi'],
                'met': ['p', 'T', 'RH'],
                'hkd': ['lat', 'lon']}
        # TODO generate complete list of variables for MET and HKD (maybe with vars_optional)

        # TODO: work with d=make_xr_dict and xr.Dataset.from_dict(d) for each instance in read-in data
        # TODO: combine with xr.concat or similar
        # TODO: use HKD for evaluating scan time



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

    # TODO: for combining RPG files to time series use xarray dataset. For writing, minght maybe still use netCDF4