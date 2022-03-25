import numpy as np

from mwr_raw2l1.errors import CoordinateError, MissingDataSource
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_helpers import merge_aux_data, scanflag_from_ele
from mwr_raw2l1.measurement.radiometrics_helpers import radiometrics_to_datasets
from mwr_raw2l1.measurement.rpg_helpers import merge_brt_blb, rpg_to_datasets


DTYPE_SCANFLAG = 'u1'  # data type used for scanflags set by Measurement class


class Measurement(object):
    def __init__(self):
        self.data = None

    def run(self, conf_inst=None):
        self.set_coord(conf_inst)
        self.set_statusflag()

    @classmethod
    def from_rpg(cls, readin_data):
        """constructor for data read in from RPG instruments.

        Auxiliary data are merged to time grid of MWR data. Scanning MWR data are returned as time series (no ele dim)

        Args:
            readin_data: dictionary with (list of) instance(s) for each RPG read-in class (keys correspond to filetype)
        Returns:
            an instance of the Measurement class with observations filled to self.data
        """

        # dimensions and variable names for usage with make_dataset
        dims = {'brt': ['time', 'frequency'],
                'blb': ['time', 'frequency', 'scan_ele'],
                'irt': ['time', 'ir_wavelength'],
                'met': ['time'],
                'hkd': ['time']}
        vars = {'brt': ['Tb', 'rainflag', 'ele', 'azi'],
                'blb': ['Tb', 'T', 'rainflag', 'scan_quadrant'],  # TODO: find a way to infer 'azi' from blb
                'irt': ['IRT', 'rainflag', 'ele', 'azi'],
                'met': ['p', 'T', 'RH'],
                'hkd': ['alarm']}
        vars_opt = {'brt': [],
                    'blb': [],
                    'irt': [],
                    'met': ['windspeed', 'winddir', 'rainrate'],
                    'hkd': ['lat', 'lon', 'T_amb_1', 'T_amb_2', 'T_receiver_kband', 'T_receiver_vband',
                            'Tstab_kband', 'Tstab_vband', 'flashmemory_remaining', 'BLscan_active']}
        # TODO : check what other hkd variables are needed for output statusflag and monitoring!!!
        scanflag_values = {'brt': 0, 'blb': 1}  # for generating a scan flag indicating whether scanning or zenith obs

        logger.info('Creating instance of Measurement class')

        # require mandatory data sources
        if ('brt' not in readin_data and 'blb' not in readin_data) or (
                not readin_data['brt'] and not readin_data['blb']):
            raise MissingDataSource('At least one file of brt (zenith MWR) or blb (scanning MWR) must be present')
        if 'hkd' not in readin_data or not readin_data['hkd']:
            raise MissingDataSource('The housekeeping file (hkd) must be present')

        # construct datasets
        all_data = rpg_to_datasets(readin_data, dims, vars, vars_opt)

        # infer MWR data sources (BRT and/or BLB) and add scanflag
        mwr_sources_present = []
        for src, flagval in scanflag_values.items():
            if src in all_data and all_data[src]:  # check corresponding data series is not an empty list
                mwr_sources_present.append(src)
                flags_here = flagval * np.ones(np.shape(all_data[src].time), dtype=DTYPE_SCANFLAG)
                all_data[src]['scanflag'] = ('time', flags_here)
        mwr_data = merge_brt_blb(all_data)

        # init measurement class and merge BRT and BLB data to time series of brightness temperatures
        out = cls()
        out.data = merge_aux_data(mwr_data, all_data)

        # round to ms to exclude rounding differences for scan transformation from different computers
        out.data['time'] = out.data.time.dt.round('ms')  # TODO: rather move to scan_transform.py

        return out

    @classmethod
    def from_radiometrics(cls, readin_data):
        """constructor for data read in from RPG instruments.

        Auxiliary data are merged to time grid of MWR data.

        Args:
            readin_data: instance or list of instances for the Radiometrics read-in class
        Returns:
            an instance of the Measurement class with observations filled to self.data
        """
        # dimensions and variable names for usage with make_dataset
        dims = {'mwr': ['time', 'frequency'],
                'aux': ['time', 'ir_wavelength']}  # TODO: wavelength was added in reader, if from config better here
        vars = {'mwr': ['Tb', 'ele', 'azi', 'quality'],
                'aux': ['IRT', 'p', 'T', 'RH', 'rainflag', 'quality']}
        vars_opt = {'mwr': [],
                    'aux': []}

        logger.info('Creating instance of Measurement class')

        all_data = radiometrics_to_datasets(readin_data, dims, vars, vars_opt)
        flags_here = scanflag_from_ele(all_data['mwr']['ele']).astype(DTYPE_SCANFLAG)
        all_data['mwr']['scanflag'] = ('time', flags_here)

        out = cls()
        out.data = merge_aux_data(all_data['mwr'], all_data)

        return out

    @classmethod
    def from_attex(cls, read_in_data):
        pass

    def set_coord(self, conf_inst, primary_src='data', delta_lat=0.01, delta_lon=0.02, delta_altitude=10):
        """(re)set coordinate variables (lat, lon, altitude) in self.data from datafile input and configuration

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

        # matching of variable names between self.data and conf and between data variables and accuracy limits
        var_data_conf = {'lat': 'station_latitude', 'lon': 'station_longitude', 'altitude': 'station_altitude'}
        acc_matching = {'lat': delta_lat, 'lon': delta_lon, 'altitude': delta_altitude}

        # strategy: do nothing if using variable from data, reset if using variable from config
        if conf_inst is None:  # no config input
            for var in var_data_conf.keys():
                if var not in self.data.keys():
                    raise CoordinateError("Cannot set coordinates. 'conf_inst' was set to None, but '{}' is missing "
                                          'in read in data'.format(var))
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
    from mwr_raw2l1.readers.reader_rpg import read_multiple_files
    from mwr_raw2l1.readers.reader_radiometrics import Reader as ReaderRadiometrics
    from mwr_raw2l1.utils.file_utils import abs_file_path, get_files

    # files = get_files(abs_file_path('mwr_raw2l1/data/rpg/0-20000-0-06610/'), 'MWR_0-20000-0-06610_A')
    # all_data = read_multiple_files(files)
    # meas = Measurement.from_rpg(all_data)
    # meas.run()

    rd = ReaderRadiometrics(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    meas = Measurement.from_radiometrics(rd)
    # meas.run()  # TODO: meas.run seems to need config for Radiometrics instruments
    pass
