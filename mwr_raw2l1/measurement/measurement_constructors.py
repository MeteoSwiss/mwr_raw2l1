import numpy as np
import xarray as xr

from mwr_raw2l1.errors import MissingDataSource
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_construct_helpers import (attex_to_datasets, check_temporal_consistency,
                                                                  merge_aux_data, merge_brt_blb,
                                                                  radiometrics_to_datasets, rpg_to_datasets, rpg_to_si)
from mwr_raw2l1.measurement.measurement_helpers import channels2quantity, is_var_in_data, channels2receiver
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
        """constructor for data read in from Radiometrics instruments.

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
                'aux': ['time']}
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
                'hkd': ['time', 'channels_rec']}
        vars = {'brt': ['Tb', 'rainflag', 'ele', 'azi'],
                'blb': ['Tb', 'T', 'rainflag', 'scan_quadrant'],
                'irt': ['IRT', 'rainflag', 'ele', 'azi'],  # ele/azi will become ele_irt/azi_irt as also present in MWR
                'met': ['p', 'T', 'RH'],
                'hkd': ['alarm']}
        vars_opt = {'brt': [],
                    'blb': [],
                    'irt': [],
                    'met': ['windspeed', 'winddir', 'rainrate'],
                    'hkd': ['lat', 'lon', 'T_amb_1', 'T_amb_2', 'T_receiver_hum', 'T_receiver_temp', 'statusflag',
                            'Tstab_hum', 'Tstab_temp', 'flashmemory_remaining', 'BLscan_active',
                            'channel_quality_ok_hum', 'channel_quality_ok_temp',
                            'noisediode_ok_hum', 'noisediode_ok_temp',
                            'Tstab_ok_hum', 'Tstab_ok_temp', 'Tstab_ok_amb']}

        scanflag_values = {'brt': 0, 'blb': 1}  # for generating a scan flag indicating whether scanning or zenith obs
        max_azi_offset = 1  # maximum offset between all values in azimuth vector to be considered identical (degrees)

        logger.info('Creating instance of Measurement class from RPG data')

        # require mandatory data sources
        if ('brt' not in readin_data and 'blb' not in readin_data) or (
                not readin_data['brt'] and not readin_data['blb']):
            raise MissingDataSource('At least one file of brt (zenith MWR) or blb (scanning MWR) must be present')
        if 'hkd' not in readin_data or not readin_data['hkd']:
            raise MissingDataSource('The housekeeping file (hkd) must be present')

        # construct datasets and check they cover same time period
        all_data = rpg_to_datasets(readin_data, dims, vars, vars_opt)
        all_data = rpg_to_si(all_data)
        check_temporal_consistency(all_data)

        # infer MWR data sources (BRT and/or BLB) and add scanflag
        mwr_sources_present = []
        for src, flagval in scanflag_values.items():
            if src in all_data and all_data[src]:  # check corresponding data series is not an empty list
                mwr_sources_present.append(src)
                flags_here = flagval * np.ones(np.shape(all_data[src].time), dtype=DTYPE_SCANFLAG)
                all_data[src]['scanflag'] = ('time', flags_here)
        mwr_data = merge_brt_blb(all_data)

        # merge auxiliary data
        all_data['irt'] = all_data['irt'].rename({'azi': 'azi_irt'})  # otherwise azi_irt set as azi if BRT file absent
        data = merge_aux_data(mwr_data, all_data)

        # take mean of ambient temperature load (one load with two temperature sensors (code works with up to 9))
        tamb_vars = [var for var in data.data_vars if var[:-1] == 'T_amb_']
        t_amb = data[tamb_vars].to_array(dim='tmpdim').mean(dim='tmpdim', skipna=True)

        # use T_met instead of T from BLB for temperature (T not available in BRT)
        if is_var_in_data(data, 'T_met'):  # assume that if there is one non-NaN in T_met, whole timeseries is there
            # cleaner but too slow would be to use mwr_raw2l1.measurement.measurement_helpers.is_full_var_in_data, e.g.:
            # - cleanest check but very slow:
            #     is_full_var_in_data(data, 'T_met')
            # - much faster check but leading to changing temperature source (MET or BLB) depending on presence of BRT:
            #     not is_full_var_in_data(data, 'T') and is_var_in_data(data, 'T_met')
            data['T'] = data['T_met']

        # if possible re-use azi from BRT and correct with scan_quadrant during scns
        if 'azi' in data:
            azi_med = data['azi'].median(skipna=True)  # outside if-clause for re-using below
            if any(data['azi'].isnull()) and \
                    (data['azi'].max(skipna=True) - data['azi'].min(skipna=True)) < max_azi_offset:
                data['azi'] = data['azi'].fillna(azi_med)
            # apply scan_quadrant for BLB azimuth (azi for scan_quadrant=1 already correct)
            if 'scan_quadrant' in data:  # mandatory for BLB, but not present for BRT where azi can be left as is
                data['azi'][data['scan_quadrant'] == 2] = np.mod(azi_med + 180, 360)
                data['azi'][data['scan_quadrant'] == 0] = np.nan

        # find out retrieval boards and quantities
        rec_quant_match = channels2quantity(data['frequency'])
        receiver = channels2receiver(data['frequency'])

        # set receiver-dependent variables (attribute _receiver_hum and _receiver_temp to _receiver_n )
        vars_in_out = {'T': 'T_rec',
                      'T_amb': 'T_amb'}
        data['T_amb_receiver_hum'] = t_amb  # need to attribute common T_amb to both receivers
        data['T_amb_receiver_temp'] = t_amb  # need to attribute common T_amb to both receivers
        for var_in, var_out in vars_in_out.items():
            for rec_nb, rec_quant in rec_quant_match.items():
                varname_in = '{}_receiver_{}'.format(var_in, rec_quant)
                varname_out = '{}_receiver_{}'.format(var_out, rec_nb)
                data[varname_out] = data[varname_in]

        # combine quality flags of different receiver boards
        data['channel_quality_ok'] = xr.DataArray(data=np.full([len(data.time), len(data.frequency)], np.nan),
                                                  dims=['time', 'frequency'])
        counters = {'hum': 0, 'temp': 0}
        for n, _ in enumerate(data['frequency']):
            quant = rec_quant_match[receiver[n]]
            ind = counters[quant]
            data['channel_quality_ok'][:, n] = data['channel_quality_ok_'+quant][:, ind]
            counters[quant] += 1

        data['mfr'] = 'rpg'  # manufacturer (lowercase)

        return cls(data, conf_inst)
