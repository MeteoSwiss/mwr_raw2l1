import numpy as np
import xarray as xr

from mwr_raw2l1.errors import DimensionError, MissingInputArgument
from mwr_raw2l1.log import logger


def make_dataset(data, dims, vars, vars_opt=None, time_vector=None):
    """generate a xarray Dataset from 'data' using the dimensions and variables specified

    Args:
        data: dictionary containing the data. If set to None or empty a placeholder dataset with all-NaN time series
            (except variable IRT, which is 2d) is returned. If set to None or empty time_vector must be specified.
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt (optional): list of keys that are optional data variables (added as 1-d series of NaN if not in 'data')
        time_vector: numpy array of datetime64 to take as time dimension for generating all-NaN datasets. This argument
            will be ignored as long as data is not None or empty
    Returns:
        xarray.Dataset
    """

    # config for empty datasets or variables
    missing_val = np.nan
    multidim_vars = {'IRT': 2, 'Tb': 2, 'Tb_scan': 3}  # variables that are not timeseries (key: varname; value: ndims)

    # init
    if vars_opt is None:
        vars_opt = []
    all_vars = vars + vars_opt

    # prepare for empty variables
    ndims_per_var = {var: 1 for var in dims + all_vars}
    for var, nd in multidim_vars.items():  # can grow larger than keys that  shall be in dataset, only accessed by key
        ndims_per_var[var] = nd

    # prepare all NaN-variables for case of data==None or empty
    if data is None or not data:
        if time_vector is None:
            raise MissingInputArgument('if data is empty or None the input argument time_vector must be specified')
        data = {'time': time_vector}  # start overwriting empty data variable
        for dim in dims[1:]:  # assume first dimension to be 'time'
            data[dim] = np.array([missing_val])  # other dimensions all one-element
        for var in all_vars:
            shape_act = [len(data[dims[k]]) for k in range(ndims_per_var[var])]
            data[var] = np.full(shape_act, missing_val)

    # add optional variables as NaN-series to data if not in input data
    for varo in vars_opt:
        if varo not in data:
            shape_act = [len(data[dims[k]]) for k in range(ndims_per_var[varo])]
            data[varo] = np.full(shape_act, missing_val)
            logger.info('Optional variable {} not found in input data. Will create a all-NaN placeholder'.format(varo))

    # collect specifications and data for generating xarray Dataset from dict
    spec = {}
    for dim in dims:
        spec[dim] = dict(dims=dim, data=data[dim])
    # add vars to spec
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
