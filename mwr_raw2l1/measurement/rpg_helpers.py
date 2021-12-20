import xarray as xr

from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement_helpers import drop_duplicates, make_dataset
from mwr_raw2l1.measurement.scan_transform import scan_to_timeseries_from_aux


def to_datasets(data, dims, vars, vars_opt):
    """generate unique xarray Datasets for each type of observations in 'data' using dimensions and variables specified

    Args:
        data: dictionary of lists containing the obs (obs: a dictionary of variable names and values) for different
            source files of same type
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        dictionary of xarray.Dataset's. It contains one item for each key in data
    """
    out = {}
    for src, data_series in data.items():
        data_act = []
        if not data_series:  # fill in NaN variables if meas source does not exist (loop over empty data_series skipped)
            logger.info('No {}-data available. Will generate a dataset fill values only for {}'.format(src, src))
            min_time = min([x.data['time'][0] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            max_time = max([x.data['time'][-1] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            data_act.append(make_dataset(None, dims[src], vars[src], vars_opt[src], time_vector=[min_time, max_time]))
        for dat in data_series:  # make a xarray dataset from the data dict in each class instance of the list
            data_act.append(make_dataset(dat.data, dims[src], vars[src], vars_opt[src]))
        out[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
        out[src] = drop_duplicates(out[src], dim='time')  # remove duplicate measurements
    return out


def merge_brt_blb(all_data):
    """merge brt (zenith MWR) and blb (scanning MWR) observations from an RPG instrument

    Args:
        all_data: dictionary of xarray.Dataset's (output of to_datasets)
    """
    if 'brt' in all_data:
        out = all_data['brt']
    if 'blb' in all_data:
        if 'brt' in all_data:
            # TODO: merge BRT and BLB as sketched in next lines after finishing transform to scan
            blb_ts = scan_to_timeseries_from_aux(all_data['blb'], hkd=all_data['hkd'], brt=all_data['brt'])
            # out = out.data.merge(blb_ts, join='outer')  # hope merge works, but don't forget to test
        else:
            out = scan_to_timeseries_from_aux(all_data['blb'], hkd=all_data['hkd'])

    return out
