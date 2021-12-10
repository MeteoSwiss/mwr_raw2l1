import xarray as xr

from mwr_raw2l1.measurement_helpers import drop_duplicates, make_dataset


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
                            'Tstab_kband', 'Tstab_vband', 'flashmemory_remaining', 'BLscan_active']}
        # TODO : check what other hkd variables are needed for output statusflag and monitoring!!!

        out = cls
        all_data = {}
        for src, data_series in readin_data.items():
            data_act = []
            for dat in data_series:  # make an xarray dataset from the data dict in each class instance
                data_act.append(make_dataset(dat.data, dims[src], vars[src], vars_opt[src]))
            all_data[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
            all_data[src] = drop_duplicates(all_data[src], dim='time')

        # merge BRT and BLB data to time series of brightness temperatures
        out.data = all_data['brt']
        # TODO: merge BRT and BLB as sketched in next lines
        # blb_ts = cls.scan_to_timeseries(all_data['blb'], all_data['brt'], all_data['hkd'])
        # out.data = out.data.merge(blb_ts, join='outer')  # hope merge works, but don't forget to test

        # bring other data to time grid of brightness temperatures
        for src in readin_data:
            # BRT and BLB data already treated
            if src in ['brt', 'blb']:
                continue

            # to make sure no variable is overwritten rename duplicates by suffixing it with its source
            for var in out.data:
                if var in all_data[src]:
                    varname_map = {var: var + '_' + src}
                    all_data[src] = all_data[src].rename(varname_map)

            # merge into out.data
            out.data = out.data.merge(all_data[src], join='left')

        return out

    @classmethod
    def from_radiometrics(cls, readin_data):
        pass

    @classmethod
    def from_attex(cls, read_in_data):
        pass

    def scan_to_timeseries(self, blb, brt, hkd=None):
        pass
        # TODO: re-use method from reader (should not stay there)
        # find last time in brt before scan: brt.sel(time=blb['time'][ind_act], method='pad')
        # find first time in brt after scan: brt.sel(time=blb['time'][ind_act], method='backfill')
        # ind_act = 0 (-1) might cause an error with pad (backfill)
        # don't forget to remove elevation dimension


if __name__ == '__main__':
    from mwr_raw2l1.reader_rpg import read_all

    all_data = read_all('data/rpg/', 'C00-V859')
    meas = Measurement.from_rpg(all_data)
    pass

