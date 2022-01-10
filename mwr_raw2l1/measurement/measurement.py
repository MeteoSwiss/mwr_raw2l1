import numpy as np

from mwr_raw2l1.errors import MissingDataSource
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.rpg_helpers import merge_brt_blb, to_datasets


class Measurement(object):
    def __init__(self):
        self.data = None

    @classmethod
    def from_rpg(cls, readin_data):
        """constructor for data read in from RPG instruments.

        Auxiliary data are merged to time grid of MWR data. Scanning MWR data are returned as time series (no ele dim)

        Args:
            readin_data: dictionary with list of instances for each RPG read-in class (keys correspond to filetype)
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
                'blb': ['Tb', 'T', 'rainflag', 'scan_quadrant'],
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
        if 'brt' not in readin_data and 'blb' not in readin_data:
            raise MissingDataSource('At least one file of brt (zenith MWR) or blb (scanning MWR) must be present')
        if 'hkd' not in readin_data:
            raise MissingDataSource('The housekeeping file (hkd) must be present')

        # construct datasets
        all_data = to_datasets(readin_data, dims, vars, vars_opt)

        # infer MWR data sources (BRT and/or BLB) and add scanflag
        mwr_sources_present = []
        for src, flagval in scanflag_values.items():
            if src in all_data and all_data[src]:  # check corresponding data series is not an empty list
                mwr_sources_present.append(src)
                all_data[src]['scaflag'] = ('time', flagval * np.ones(np.shape(all_data[src].time), dtype='u1'))
        mwr_data = merge_brt_blb(all_data)

        # init measurement class and merge BRT and BLB data to time series of brightness temperatures
        out = cls()
        out.data = mwr_data

        # bring other data to time grid of brightness temperatures
        for src in readin_data:
            if src in ['brt', 'blb']:  # BRT and BLB data already treated
                continue

            # to make sure no variable is overwritten rename duplicates by suffixing it with its source
            for var in all_data[src]:
                if var in out.data:
                    varname_map = {var: var + '_' + src}
                    all_data[src] = all_data[src].rename(varname_map)

            # interp to same time grid (time grid from blb now stems from some interp) and merge into out.data
            srcdat_interp = all_data[src].interp(time=out.data['time'], method='nearest')  # nearest: flags stay integer
            out.data = out.data.merge(srcdat_interp, join='left')

        # TODO: check out.data for consistency, possibly with plotting etc.
        return out

    @classmethod
    def from_radiometrics(cls, readin_data):
        pass

    @classmethod
    def from_attex(cls, read_in_data):
        pass

    def encode_statusflag(self):
        pass

    def run(self):
        self.encode_statusflag()


if __name__ == '__main__':
    from mwr_raw2l1.readers.reader_rpg import read_multiple_files
    from mwr_raw2l1.utils.file_utils import abs_file_path, get_files

    files = get_files(abs_file_path('mwr_raw2l1/data/rpg/0-20000-0-06610/'), 'MWR_0-20000-0-06610_A')
    all_data = read_multiple_files(files)
    meas = Measurement.from_rpg(all_data)
    meas.run()
