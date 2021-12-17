from mwr_raw2l1.measurement.measurement_helpers import rpg_to_datasets
from mwr_raw2l1.measurement.scan_transform import scan_to_timeseries_from_aux


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

        out = cls()
        all_data = rpg_to_datasets(readin_data, dims, vars, vars_opt)

        all_data['brt']

        # merge BRT and BLB data to time series of brightness temperatures
        out.data = all_data['brt']
        # TODO: merge BRT and BLB as sketched in next lines
        blb_ts = scan_to_timeseries_from_aux(all_data['blb'], hkd=all_data['hkd'], brt=all_data['brt'])
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


if __name__ == '__main__':
    from mwr_raw2l1.readers.reader_rpg import read_all

    all_data = read_all('../data/rpg/', 'C00-V859')
    meas = Measurement.from_rpg(all_data)
    pass
