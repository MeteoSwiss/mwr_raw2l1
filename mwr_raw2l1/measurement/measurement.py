import numpy as np

from mwr_raw2l1.errors import CoordinateError
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_constructors import MeasurementConstructors


class Measurement(MeasurementConstructors):

    def run(self, conf_inst=None):
        # TODO: implement a checker looking if all needed variables are present
        self.set_coord(conf_inst)
        self.set_statusflag()

    def set_coord(self, conf_inst, primary_src='data', delta_lat=0.01, delta_lon=0.02, delta_altitude=10):
        """(re)set geographical coordinates (lat, lon, altitude) in self.data from datafile input and configuration

        If both are available the method checks consistency between coordinates in datafile and configuration.

        Args:
            conf_inst: configuration dictionary for instrument containing keys station_latitude, station_longitude and
                station_altitude. If set to None, coordinates are taken from datafile without any checks and an error is
                raised if any of lat, lon or altitude is missing in data.
            primary_src (optional {'data', 'config'}): specifies which source takes precedence. Defaults to 'data'
            delta_lat (optional): maximum allowed difference between latitude in config and in datafile in degrees.
                Defaults to 0.01.
            delta_lon (optional): maximum allowed difference between longitude in config and in datafile in degrees.
                Defaults to 0.02.
            delta_altitude (optional): maximum allowed difference between altitude in config and in datafile in meters.
                Defaults to 10.
        """

        # matching of variable names between self.data and conf
        var_data_conf = {'lat': 'station_latitude', 'lon': 'station_longitude', 'altitude': 'station_altitude'}
        # matching between data variables and accuracy limits
        acc_matching = {'lat': delta_lat, 'lon': delta_lon, 'altitude': delta_altitude}

        # strategy: do nothing if using variable from data, reset if using variable from config
        if conf_inst is None:  # no config input
            for var in var_data_conf.keys():
                if var not in self.data.keys():
                    raise CoordinateError("Cannot set coordinates. 'conf_inst' was set to None, but '{}' is missing "
                                          'in data read in from data file'.format(var))
        elif not all(var in conf_inst for var in var_data_conf.values()):  # missing keys in config
            err_msg = "'conf_inst' needs to contain all of the following keys: {}".format(list(var_data_conf.values()))
            raise CoordinateError(err_msg)
        else:  # necessary values present in config
            for var, acc in acc_matching.items():
                if var in self.data:
                    if abs(self.data[var][0] - conf_inst[var_data_conf[var]]) > acc:  # checking all elements too slow
                        raise CoordinateError("'{}' in data and conf differs by more than {}".format(var, acc))
                if primary_src == 'config' or var not in self.data:  # (re)set variable according to conf_inst
                    self.data[var] = (('time',), np.full(self.data.time.shape, conf_inst[var_data_conf[var]]))
                    logger.info("Using '{}' from config as coordinate variable".format(var_data_conf[var]))
                else:
                    logger.info("Using '{}' from data files as coordinate variable".format(var))

    def set_statusflag(self):
        """set statusflag from data"""
        pass  # TODO: Implement method for setting statusflag from data (and possibly conf_inst)


if __name__ == '__main__':
    from mwr_raw2l1.readers.reader_attex import Reader as ReaderAttex
    from mwr_raw2l1.readers.reader_radiometrics import Reader as ReaderRadiometrics
    from mwr_raw2l1.readers.reader_rpg import read_multiple_files
    from mwr_raw2l1.utils.config_utils import get_inst_config
    from mwr_raw2l1.utils.file_utils import abs_file_path, get_files

    # RPG
    conf_rpg = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
    files = get_files(abs_file_path('mwr_raw2l1/data/rpg/0-20000-0-06610/'), 'MWR_0-20000-0-06610_A')
    all_data = read_multiple_files(files)
    meas = Measurement.from_rpg(all_data)
    meas.run(conf_rpg)

    # Radiometrics
    conf_radiometrics = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-10393_A.yaml'))
    rd = ReaderRadiometrics(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    meas = Measurement.from_radiometrics(rd)
    meas.run(conf_radiometrics)

    # Attex
    rd = ReaderAttex(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    meas = Measurement.from_attex(rd)
    pass
