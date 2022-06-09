import numpy as np
import xarray as xr

from mwr_raw2l1.errors import MissingConfig, MWRDataError, DimensionMismatch
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_constructors import MeasurementConstructors
from mwr_raw2l1.measurement.measurement_helpers import channels2receiver, get_receiver_vars
from mwr_raw2l1.measurement.measurement_qc_helpers import check_rain, check_receiver_sanity, check_sun
from mwr_raw2l1.utils.num_utils import setbit, timedelta2s, unsetbit


class Measurement(MeasurementConstructors):

    def run(self, conf_qc):
        """main method of the class completing dimensions and variables and applying quality flags

        Args:
            conf_qc: configuration dictionary of the quality control. For defaults use mwr_raw2l1/config/qc_config.yaml
        """
        self.set_coords()
        self.set_wavelength()
        self.set_receivers()
        self.set_inst_params()
        self.set_time_bnds()
        self.apply_quality_control(conf_qc)

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
        """(re)set wavelength of infrared radiometer in self.data accounting for self.conf_inst. Also add as dimension.

        If conf and data are available the method checks consistency between wavelength in datafile and configuration.
        For self.conf_inst to be usable it must contain key ir_wavelength.
        If self.conf_inst is None, variables are taken from datafile without any checks and an error is raised if any
        variable is missing in data.

        Args:
            delta (optional): maximum allowed difference between IR wavelength in config and in datafile in nm.
                Defaults to 1.
            **kwargs: keyword arguments passed on to :meth:`set_vars`
        """
        varname_wavelength = 'ir_wavelength'

        # if wavelength not present in data pre-allocate with a NaN dimension. Can be overwritten by config in next step
        if varname_wavelength not in self.data.dims:
            self.data = self.data.assign_coords({varname_wavelength: np.full((1,), np.nan)})

        varname_data_conf = {varname_wavelength: 'ir_wavelength'}
        delta_data_conf = {varname_wavelength: delta}
        self.set_vars(varname_data_conf, delta_data_conf, dim=varname_wavelength, **kwargs)

    def set_receivers(self):
        """set receiver dimension and receiver-specific variables"""
        receiver_dim_name = 'receiver_nb'  # name of the dimension containing the receiver numbers

        # set dimension receiver_dim_name and variable 'receiver'
        self.data['receiver'] = (('frequency',), channels2receiver(self.data['frequency']))
        receiver_nbs = np.unique(self.data['receiver'])
        self.data = self.data.assign_coords({receiver_dim_name: receiver_nbs})

        # set receiver-dependent variables
        rec_vars = get_receiver_vars(self.data.variables)
        for outvar, vars in rec_vars.items():
            if len(vars) != len(self.data[receiver_dim_name]):
                raise DimensionMismatch("expected to get data from {} receivers when setting '{}', but got from {} ({})"
                                        .format(len(self.data[receiver_dim_name]), outvar, len(vars), vars))
            self.data[outvar] = xr.concat([self.data[var] for var in vars], dim=receiver_dim_name)
        pass

    def set_inst_params(self):
        """set instrument dependent parameters which are not dimensions (must be set before)"""

        freq_vars = {'freq_shift': 'freq_shift', 'bandwidth': 'bandwidth', 'beamwidth': 'beamwidth'}
        freq_deltas = {'freq_shift': 999, 'bandwidth': 999, 'beamwidth': 999}
        self.set_vars(freq_vars, freq_deltas, dim='frequency', accept_unset=True)

        ir_vars = {'ir_bandwidth': 'ir_bandwidth', 'ir_beamwidth': 'ir_beamwidth'}
        ir_deltas = {'ir_bandwidth': 999, 'ir_beamwidth': 999}
        self.set_vars(ir_vars, ir_deltas, dim='ir_wavelength', accept_unset=True)

    def set_vars(self, varname_data_conf, delta_data_conf, dim='time', primary_src='data', accept_unset=False):
        """(re)set variable in self.data from datafile input and instrument configuration file

        If both are available the method checks consistency between coordinates in datafile and configuration.
        If self.conf_inst is None, variables are taken from datafile without any checks and an error is raised if any
        variable is missing in data.

        Args:
            varname_data_conf: dictionary for matching between variable names in data (keys) and config (values)
            delta_data_conf: dictionary of maximum difference allowed between value in data and config (values) for each
                variable. Keys are the variable names in data.
            dim (optional): dimension of the variables to set. Set to None for dimensionless vars. Defaults to 'time'
            primary_src (optional {'data', 'config', 'conf'}): specifies which source takes precedence. Default: 'data'
            accept_unset (optional): accept unset variables if neither present in data nor conf_inst. Defaults to False
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
                base_msg = "'conf_inst' needs to contain all of the following keys as not all are in data: {}.".format(
                    list(varname_data_conf.values()))
                if accept_unset:
                    logger.warning(base_msg + ' Some or all of these variables will be unset')
                else:
                    raise MissingConfig(base_msg + ' To allow these to be unset, call method with accept_unset=True')

        # necessary values present in config
        else:
            for var, acc in delta_data_conf.items():
                # check values from config and data do not differ by too much
                if var in self.data and not all(np.isnan(self.data[var])):
                    if abs(self.data[var][0] - self.conf_inst[varname_data_conf[var]]) > acc:  # speed: only check [0]
                        raise MWRDataError("'{}' in data and conf differs by more than {}".format(var, acc))
                # (re)set variable according to conf_inst
                if primary_src in ['config', 'conf'] or var not in self.data or all(np.isnan(self.data[var])):
                    if dim is None:
                        self.data[var] = ((), self.conf_inst[varname_data_conf[var]])
                    else:
                        self.data[var] = ((dim,), np.full(self.data[dim].shape, self.conf_inst[varname_data_conf[var]]))
                    logger.info("Using '{}' from config".format(varname_data_conf[var]))
                # keep value from data files
                else:
                    logger.info("Using '{}' from data files".format(var))

    def set_time_bnds(self):
        """set time bounds from spacing of time vector and scanflag"""

        # infer integration time from data
        delta_t = np.diff(self.data['time'])
        scandiff_flag = np.logical_and(self.data['scanflag'][:-1], np.roll(self.data['scanflag'], -1)[:-1])
        starediff_flag = np.logical_and(self.data['scanflag'][:-1] == 0, np.roll(self.data['scanflag'], -1)[:-1] == 0)

        inttime_scan = np.timedelta64(0, 'ns')  # in case int time cannot be determined, time_bnds = [time, time]
        inttime_stare = np.timedelta64(0, 'ns')
        if np.any(scandiff_flag):
            inttime_scan = np.timedelta64(int(timedelta2s(np.median(delta_t[scandiff_flag]))), 's')  # floor to seconds
        if np.any(starediff_flag):
            inttime_stare = np.timedelta64(int(timedelta2s(np.median(delta_t[starediff_flag]))), 's')  # floor to sec

        inttime = np.full(self.data['time'].shape, np.nan, dtype='timedelta64[ns]')
        inttime[self.data['scanflag'] != 0] = inttime_scan
        inttime[self.data['scanflag'] == 0] = inttime_stare

        # set dimension 'bnds' and variable 'time_bnds'
        self.data.assign_coords({'bnds': ['start', 'end']})
        self.data['time_bnds'] = (('time', 'bnds'),
                                  np.full((len(self.data['time']), 2), np.nan, dtype='datetime64[ns]'))
        self.data['time_bnds'][:, 0] = self.data['time'] - inttime
        self.data['time_bnds'][:, 1] = self.data['time']

    def apply_quality_control(self, conf_qc):
        """set quality_flag and quality_flag_status and qc_thresholds according to quality control"""

        n_bits = 8  # number of bits in quality flag

        logger.info('Setting quality_flag and quality_flag_status')

        # initialise quality_flag with 'all good' and quality_flag_status with 'nothing checked'. Dim=(time, frequency)
        self.data['quality_flag'] = xr.zeros_like(self.data['Tb'], dtype=np.int32)
        self.data['quality_flag_status'] = xr.ones_like(self.data['quality_flag'], dtype=np.int32) * (2**n_bits - 1)
        qc_thresholds = 'Thresholds used for quality control:'  # used to set self.data['qc_thresholds']

        # check for expected shape
        n_channels = self.data['quality_flag'].sizes['frequency']
        if n_channels != self.data['quality_flag'].shape[1]:
            raise MWRDataError("expected 'Tb' and 'quality_flag' of dimension (time, frequency) but found shape={} and "
                               'len(frequency)={}'.format(self.data['quality_flag'].shape, len(self.data.frequency)))

        # perform channel-independent quality checks (generate masks for usage in following loop)
        if conf_qc['check_rain']:
            mask_rain, check_rain_applied = check_rain(self.data)
        if conf_qc['check_sun']:
            mask_sun, check_sun_applied = check_sun(self.data, conf_qc['delta_ele_sun'], conf_qc['delta_azi_sun'])

        # set quality_flag and quality_flag_status for each channel
        for ch in range(n_channels):
            # bit 0
            if conf_qc['check_missing_Tb']:
                self._setbits_qc(bit_nb=0, channel=ch, mask_fail=self.data['Tb'][:, ch].isnull())
            # bit 1
            if conf_qc['check_min_Tb']:
                self._setbits_qc(bit_nb=1, channel=ch, mask_fail=(self.data['Tb'][:, ch] < conf_qc['Tb_threshold'][0]))
            # bit 2
            if conf_qc['check_min_Tb']:
                self._setbits_qc(bit_nb=2, channel=ch, mask_fail=(self.data['Tb'][:, ch] > conf_qc['Tb_threshold'][1]))
            # bit 3
            if conf_qc['check_spectral_consistency']:
                # TODO: ask Bernhard how to best implement this. important flag, should be done.
                #       when done set check_spectral_consistency=True in conf_qc
                raise NotImplementedError('checker for spectral consistency not implemented')
            # bit 4
            if conf_qc['check_receiver_sanity']:
                mask_fail, check_applied = check_receiver_sanity(self.data, ch)
                if check_applied:
                    self._setbits_qc(bit_nb=4, channel=ch, mask_fail=mask_fail)
                else:  # if check cannot be applied to one channel, it cannot be applied to any (because a var misses)
                    conf_qc['check_receiver_sanity'] = False
            # bit 5
            if conf_qc['check_rain'] and check_rain_applied:
                self._setbits_qc(bit_nb=5, channel=ch, mask_fail=mask_rain)
            # bit 6
            if conf_qc['check_sun'] and check_sun_applied:
                self._setbits_qc(bit_nb=6, channel=ch, mask_fail=mask_sun)
            # bit 7
            if conf_qc['check_Tb_offset']:
                NotImplementedError('checker for Tb_offset not implemented')  # not most important, same for ACTRIS

        # store used thresholds as string for comment in output file
        if conf_qc['check_min_Tb']:
            qc_thresholds += ' Tb_min={},'.format(conf_qc['Tb_threshold'][0])
        if conf_qc['check_max_Tb']:
            qc_thresholds += ' Tb_max={},'.format(conf_qc['Tb_threshold'][1])
        if conf_qc['check_sun'] and check_sun_applied:
            qc_thresholds += ' delta_ele_sun={},'.format(conf_qc['delta_ele_sun'])
            qc_thresholds += ' delta_azi_sun={},'.format(conf_qc['delta_azi_sun'])
        # remove tailing comma if needed and store to self.data
        if qc_thresholds[-1] == ',':
            qc_thresholds = qc_thresholds[:-1]
        self.data['qc_thresholds'] = qc_thresholds

    def _setbits_qc(self, bit_nb, channel, mask_fail):
        """set values for quality_flag and quality_flag status for executed checks"""
        self.data['quality_flag'][mask_fail, channel] = setbit(self.data['quality_flag'][mask_fail, channel], bit_nb)
        self.data['quality_flag_status'][:, channel] = unsetbit(self.data['quality_flag_status'][:, channel], bit_nb)


if __name__ == '__main__':
    from mwr_raw2l1.readers.reader_attex import Reader as ReaderAttex
    from mwr_raw2l1.readers.reader_radiometrics import Reader as ReaderRadiometrics
    from mwr_raw2l1.readers.reader_rpg import read_multiple_files
    from mwr_raw2l1.utils.config_utils import get_inst_config, get_qc_config
    from mwr_raw2l1.utils.file_utils import abs_file_path, get_files

    conf_qc = get_qc_config(abs_file_path('mwr_raw2l1/config/qc_config.yaml'))

    # RPG
    conf_rpg = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
    files = get_files(abs_file_path('mwr_raw2l1/data/rpg/0-20000-0-06610/'), 'MWR_0-20000-0-06610_A')
    all_data = read_multiple_files(files)
    meas = Measurement.from_rpg(all_data, conf_rpg)
    meas.run(conf_qc)

    # Radiometrics
    conf_radiometrics = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-10393_A.yaml'))
    rd = ReaderRadiometrics(abs_file_path('mwr_raw2l1/data/radiometrics/orig/2021-01-31_00-04-08_lv1.csv'))
    rd.run()
    meas = Measurement.from_radiometrics(rd, conf_radiometrics)
    meas.run(conf_qc)

    # Attex
    conf_attex = get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-99999_A.yaml'))
    rd = ReaderAttex(abs_file_path('mwr_raw2l1/data/attex/orig/0mtp20211107.tbr'))
    rd.run()
    meas = Measurement.from_attex(rd, conf_attex)
    meas.run(conf_qc)
    pass
