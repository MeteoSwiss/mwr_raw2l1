import numpy as np
import xarray
import xarray as xr
from mwr_raw2l1.errors import DimensionError


def make_dataset(data, dims, vars, vars_opt=None):
    """generate a xarray Dataset from 'data' using the dimensions and variables specified

    Args:
        data: dictionary containing the data
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        xarray.Dataset
    """

    # init
    spec = {}
    if vars_opt is None:
        vars_opt = []

    # add dimensions to spec
    for dim in dims:
        spec[dim] = dict(dims=dim, data=data[dim])

    # add optional variables as NaN-series to data
    for varo in vars_opt:
        if varo not in data:
            data[varo] = np.full_like(data[dims[0]], np.nan)
            # TODO: add logger here to give info that varo is not in data

    # add vars to spec
    all_vars = vars + vars_opt
    for var in all_vars:
        nd = np.ndim(data[var])
        if nd > len(dims):
            raise DimensionError(dims, var, nd)
        spec[var] = dict(dims=dims[0:nd], data=data[var])

    return xr.Dataset.from_dict(spec)


def drop_duplicates(ds, dim):
    """drop duplicates from all data in ds for duplicates in dimension vector

    Args:
        ds: xarray Dataset or DataArray
        dim: string indicating the dimension name to check for duplicates
    Returns:
        ds with unique dimension vector
    """

    _, ind = np.unique(ds[dim], return_index=True)  # keep first index but assume duplicate values identical anyway
    return ds.isel({dim: ind})


def rpg_to_datasets(data, dims, vars, vars_opt):
    """generate unique xarray Datasets for each type of observations in 'data' using dimensions and variables specified

    Args:
        data: dictionary of lists containing the obs (obs: a dictionary of variable names and values) for different
            source files of same type
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables (added as 1-dim series of NaN if missing in 'data')
    Returns:
        dictionary of xarray.Dataset
    """
    out = {}
    for src, data_series in data.items():
        data_act = []
        for dat in data_series:  # make a xarray dataset from the data dict in each class instance
            data_act.append(make_dataset(dat.data, dims[src], vars[src], vars_opt[src]))
        out[src] = xr.concat(data_act, dim='time')  # merge all datasets of the same type
        out[src] = drop_duplicates(out[src], dim='time')
    return out
