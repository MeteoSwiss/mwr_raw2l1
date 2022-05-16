import numpy as np

from mwr_raw2l1.errors import MissingDataSource
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_construct_helpers import (attex_to_datasets, merge_aux_data, merge_brt_blb,
                                                                  radiometrics_to_datasets, rpg_to_datasets)
from mwr_raw2l1.measurement.scan_transform import scan_to_timeseries_from_scanonly, scanflag_from_ele

DTYPE_SCANFLAG = 'u1'  # data type used for scanflags set by Measurement class


class MeasurementConstructors(object):

    def __init__(self, data, conf_inst):
        self.data = data
        self.conf_inst = conf_inst

    @classmethod
    def from_attex(cls, readin_data, conf_inst=None):
        """constructor for data read in from Attex instruments.

        Args:
            readin_data: instance or list of instances for the Attex read-in class
            conf_inst (optional): dictionary of instrument configuration. Set to None if no config is needed.
                Defaults to None.
        Returns:
            instance of the Measurement class with observations filled to self.data and config to self.conf_inst
        """
        dims = ['time', 'frequency', 'scan_ele']
        vars = ['Tb', 'T']
        vars_opt = []

        logger.info('Creating instance of Measurement class from Attex data')

        mwr_data = attex_to_datasets(readin_data, dims, vars, vars_opt)
        flags_here = np.ones(np.shape(mwr_data.time), dtype=DTYPE_SCANFLAG)  # Attex always scanning > flag=1
        mwr_data['scanflag'] = ('time', flags_here)
        mwr_data = scan_to_timeseries_from_scanonly(mwr_data)

        mwr_data['mfr'] = 'attex'  # manufacturer (lowercase)

        return cls(mwr_data, conf_inst)

    @classmethod
    def from_radiometrics(cls, readin_data, conf_inst=None):
        """constructor for data read in from RPG instruments.

        Auxiliary data are merged to time grid of MWR data.

        Args:
            readin_data: instance or list of instances for the Radiometrics read-in class
            conf_inst (optional): dictionary of instrument configuration. Set to None if no config is needed.
                Defaults to None.
        Returns:
            instance of the Measurement class with observations filled to self.data and config to self.conf_inst
        """
        # dimensions and variable names for usage with make_dataset
        dims = {'mwr': ['time', 'frequency'],
                'aux': ['time', 'ir_wavelength']}  # TODO: wavelength was added in reader, if from config better here
        vars = {'mwr': ['Tb', 'ele', 'azi', 'quality'],
                'aux': ['IRT', 'p', 'T', 'RH', 'rainflag', 'quality']}
        vars_opt = {'mwr': [],
                    'aux': []}

        logger.info('Creating instance of Measurement class from Radiometrics data')

        all_data = radiometrics_to_datasets(readin_data, dims, vars, vars_opt)
        flags_here = scanflag_from_ele(all_data['mwr']['ele']).astype(DTYPE_SCANFLAG)
        all_data['mwr']['scanflag'] = ('time', flags_here)
        data = merge_aux_data(all_data['mwr'], all_data)

        data['mfr'] = 'radiometrics'  # manufacturer (lowercase)

        return cls(data, conf_inst)

    @classmethod
    def from_rpg(cls, readin_data, conf_inst=None):
        """constructor for data read in from RPG instruments.

        Auxiliary data are merged to time grid of MWR data. Scanning MWR data are returned as time series (no ele dim)

        Args:
            readin_data: dictionary with (list of) instance(s) for each RPG read-in class (keys correspond to filetype)
            conf_inst (optional): dictionary of instrument configuration. Set to None if no config is needed.
                Defaults to None.
        Returns:
            instance of the Measurement class with observations filled to self.data and config to self.conf_inst
        """

        # dimensions and variable names for usage with make_dataset
        dims = {'brt': ['time', 'frequency'],
                'blb': ['time', 'frequency', 'scan_ele'],
                'irt': ['time', 'ir_wavelength'],
                'met': ['time'],
                'hkd': ['time', 'channels']}
        vars = {'brt': ['Tb', 'rainflag', 'ele', 'azi'],
                'blb': ['Tb', 'T', 'rainflag', 'scan_quadrant'],  # TODO: ask Bernhard: find way to infer 'azi' from blb
                'irt': ['IRT', 'rainflag', 'ele', 'azi'],  # ele/azi will become ele_irt/azi_irt as also present in MWR
                'met': ['p', 'T', 'RH'],
                'hkd': ['alarm']}
        vars_opt = {'brt': [],
                    'blb': [],
                    'irt': [],
                    'met': ['windspeed', 'winddir', 'rainrate'],
                    'hkd': ['lat', 'lon', 'T_amb_1', 'T_amb_2', 'T_receiver_kband', 'T_receiver_vband', 'statusflag',
                            'Tstab_kband', 'Tstab_vband', 'flashmemory_remaining', 'BLscan_active',
                            'channel_quality_ok', 'noisediode_ok_kband', 'noisediode_ok_vband',
                            'Tstab_ok_kband', 'Tstab_ok_vband', 'Tstab_ok_amb']}
        # TODO : introduce a variable 'monitoring' in output L1 (inform task force) to collect relevant variables of HKD

        scanflag_values = {'brt': 0, 'blb': 1}  # for generating a scan flag indicating whether scanning or zenith obs

        logger.info('Creating instance of Measurement class from RPG data')

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
        data = merge_aux_data(mwr_data, all_data)

        # take mean of ambient temperature load (one load with two temperature sensors (code works with up to 9))
        tamb_vars = [var for var in data.data_vars if var[:-1] == 'T_amb_']
        data['T_amb'] = data[tamb_vars].to_array(dim='tmpdim').mean(dim='tmpdim', skipna=True)

        data['mfr'] = 'rpg'  # manufacturer (lowercase)

        return cls(data, conf_inst)
