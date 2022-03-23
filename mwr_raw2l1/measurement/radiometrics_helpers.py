import xarray as xr

from mwr_raw2l1.measurement.measurement_helpers import drop_duplicates, make_dataset


def radiometrics_to_datasets(data_all, dims, vars, vars_opt):
    """generate unique :class:`xarray.Dataset` for each type of obs in 'data' using dimensions and variables specified

    Args:
        data_all: single instance of the read-in class (with observations in instance variable 'data') or as a list
             containing a series of instances of read-in classes.
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        dictionary with one :class:`xarray.Dataset` for each key. It contains one item for each key in data
    """

    out = {}

    if not isinstance(data_all, list):  # accept also single instances of read-in class not inside a list
        data_all = [data_all]

    sources = data_all[0].data.keys()

    for src in sources:
        data_act = []
        for dat in data_all:
            data_act.append(make_dataset(dat.data[src], dims[src], vars[src], vars_opt[src]))
        out[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
        out[src] = drop_duplicates(out[src], dim='time')  # remove duplicate measurements

    return out
