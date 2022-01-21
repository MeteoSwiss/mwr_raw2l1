import xarray as xr

from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_helpers import drop_duplicates, make_dataset
from mwr_raw2l1.measurement.scan_transform import scan_to_timeseries


def to_datasets(data, dims, vars, vars_opt):
    """generate unique :class:`xarray.Dataset` for each type of obs in 'data' using dimensions and variables specified

    Args:
        data: dictionary of lists containing the obs (obs: a dictionary of variable names and values) for different
            source files of same type. The dictionary keys correspond to the type of observations (e.g. brt, blb, ...)
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        dictionary with one :class:`xarray.Dataset` for each key. It contains one item for each key in data
    """
    multidim_vars_per_obstype = {'irt': {'IRT': 2}, 'brt': {'Tb': 2}, 'blb': {'Tb': 3}}

    out = {}

    for src, data_series in data.items():
        if src in multidim_vars_per_obstype:
            multidim_vars = multidim_vars_per_obstype[src]
        else:
            multidim_vars = {}
        data_act = []
        if not data_series:  # fill in NaN variables if meas source does not exist (loop over empty data_series skipped)
            if src in ('brt', 'blb'):  # don't create empty datasets for missing MWR data
                continue
            logger.info('No {}-data available. Will generate a dataset fill values only for {}'.format(src, src))
            min_time = min([x.data['time'][0] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            max_time = max([x.data['time'][-1] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            data_act.append(make_dataset(None, dims[src], vars[src], vars_opt[src], multidim_vars=multidim_vars,
                                         time_vector=[min_time, max_time]))
        for dat in data_series:  # make a xarray dataset from the data dict in each class instance of the list
            data_act.append(make_dataset(dat.data, dims[src], vars[src], vars_opt[src], multidim_vars=multidim_vars))
        out[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
        out[src] = drop_duplicates(out[src], dim='time')  # remove duplicate measurements

    return out


def merge_brt_blb(all_data):
    """merge brt (zenith MWR) and blb (scanning MWR) observations from an RPG instrument

    Args:
        all_data: dictionary with a :class:`xarray.Dataset` attached to each key (output of :func:`to_datasets`)
    """
    if 'brt' in all_data:
        out = all_data['brt']
    if 'blb' in all_data:
        if 'brt' in all_data:
            blb_ts = scan_to_timeseries(all_data['blb'], hkd=all_data['hkd'], brt=all_data['brt'])
            out = out.merge(blb_ts, join='outer')
        else:
            out = scan_to_timeseries(all_data['blb'], hkd=all_data['hkd'])

    return out
