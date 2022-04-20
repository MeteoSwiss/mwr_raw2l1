import numpy as np

from mwr_raw2l1.errors import MissingConfig, MWRDataError
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_constructors import MeasurementConstructors


class Measurement(MeasurementConstructors):

    def run(self):
        """main method of the class"""
        self.set_coords()
        self.set_wavelength()
        self.set_statusflag()

    def set_coords(self, delta_lat=0.01, delta_lon=0.02, delta_altitude=10, **kwargs):
        """(re)set geographical coordinates (lat, lon, altitude) in self.data accounting for self.conf_inst

        If both are available the method checks consistency between coordinates in datafile and configuration.
        For self.conf_inst to be usable it must contain keys station_latitude, station_longitude and station_altitude.
        If self.conf_inst is None, variables are taken from datafile without any checks and an error is raised if any
        variable is missing in data.

        Args:
            delta_lat (optional): maximum allowed difference between latitude in config and in datafile in degrees.
                Defaults to 0.01.
            delta_lon (optional): maximum allowed difference between longitude in config and in datafile in degrees.
                Defaults to 0.02.
            delta_altitude (optional): maximum allowed difference between altitude in config and in datafile in meters.
                Defaults to 10.
            **kwargs: keyword arguments passed on to :meth:`set_vars`
        """
        varname_data_conf = {'lat': 'station_latitude', 'lon': 'station_longitude', 'altitude': 'station_altitude'}
        delta_data_conf = {'lat': delta_lat, 'lon': delta_lon, 'altitude': delta_altitude}
        self.set_vars(varname_data_conf, delta_data_conf, **kwargs)

    def set_wavelength(self, delta=1, **kwargs):
        """(re)set wavelength of infrared radiometer in self.data accounting for self.conf_inst

        If both are available the method checks consistency between wavelength in datafile and configuration.
        For self.conf_inst to be usable it must contain key ir_wavelength.
        If self.conf_inst is None, variables are taken from datafile without any checks and an error is raised if any
        variable is missing in data.

        Args:
            delta (optional): maximum allowed difference between IR wavelength in config and in datafile in nm.
                Defaults to 1.
            **kwargs: keyword arguments passed on to :meth:`set_wavelength`
        """
        varname_wavelength = 'ir_wavelength'

        # if wavelength not present in data pre-allocate with a NaN dimension. Can be overwritten by config in next step
        if varname_wavelength not in self.data.dims:
            self.data = self.data.assign_coords({varname_wavelength: np.full((1,), np.nan)})

        varname_data_conf = {varname_wavelength: 'ir_wavelength'}
        delta_data_conf = {varname_wavelength: delta}
        self.set_vars(varname_data_conf, delta_data_conf, dim=varname_wavelength, **kwargs)

    def set_vars(self, varname_data_conf, delta_data_conf, dim='time', primary_src='data'):
        """(re)set variable in self.data from datafile input and instrument configuration file

        If both are available the method checks consistency between coordinates in datafile and configuration.
        If self.conf_inst is None, variables are taken from datafile without any checks and an error is raised if any
        variable is missing in data.

        Args:
            varname_data_conf: dictionary for matching between variable names in data (keys) and config (values)
            delta_data_conf: dictionary of maximum difference allowed between value in data and config (values) for each
                variable. Keys are the variable names in data.
            dim (optional): dimension of the variables to set. Defaults to 'time'
            primary_src (optional {'data', 'config', 'conf'}): specifies which source takes precedence. Default: 'data'
        """

        # strategy: do nothing if using variable from data, reset if using variable from config

        # no config input
        if self.conf_inst is None:
            for var in varname_data_conf.keys():
                if var not in self.data.keys():
                    raise MWRDataError("Cannot set variables. 'conf_inst' was set to None, but '{}' is missing in data "
                                       'read in from data file'.format(var))
        # missing keys in config
        elif not all(var in self.conf_inst for var in varname_data_conf.values()):
            if all(var in self.data for var in varname_data_conf.keys()):
                logger.info('Using {} from data files without check by config values'
                            .format(list(varname_data_conf.keys())))
            else:
                raise MissingConfig("'conf_inst' needs to contain all of the following keys as not all are in data: "
                                    '{}'.format(list(varname_data_conf.values())))
        # necessary values present in config
        else:
            for var, acc in delta_data_conf.items():
                # check values from config and data do not differ by too much
                if var in self.data and not all(np.isnan(self.data[var])):
                    if abs(self.data[var][0] - self.conf_inst[varname_data_conf[var]]) > acc:  # speed: only check [0]
                        raise MWRDataError("'{}' in data and conf differs by more than {}".format(var, acc))

                # (re)set variable according to conf_inst
                if primary_src in ['config', 'conf'] or var not in self.data or all(np.isnan(self.data[var])):
                    self.data[var] = ((dim,), np.full(self.data[dim].shape, self.conf_inst[varname_data_conf[var]]))
                    logger.info("Using '{}' from config".format(varname_data_conf[var]))
                # keep value from data files
                else:
                    logger.info("Using '{}' from data files".format(var))

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
    meas = Measurement.from_rpg(all_data, conf_rpg)
    meas.run()

    # Radiometrics
    conf_radiometrics = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-10393_A.yaml'))
    rd = ReaderRadiometrics(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    meas = Measurement.from_radiometrics(rd, conf_radiometrics)
    meas.run()

    # Attex
    conf_attex = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-99999_A.yaml'))
    rd = ReaderAttex(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    meas = Measurement.from_attex(rd, conf_attex)
    meas.run()
    pass
