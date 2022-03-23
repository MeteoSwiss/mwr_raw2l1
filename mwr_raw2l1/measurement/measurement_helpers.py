import numpy as np
import xarray as xr

from mwr_raw2l1.errors import DimensionError, MissingInputArgument
from mwr_raw2l1.log import logger


def make_dataset(data, dims, vars, vars_opt=None, multidim_vars=None, time_vector=None):
    """generate a :class:`xarray.Dataset` from 'data' dictionary using the dimensions and variables specified

    Args:
        data: dictionary containing the data. If set to None or empty a placeholder dataset with all-NaN time series
            (except variable IRT, which is 2d) is returned. If set to None or empty time_vector must be specified.
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt (optional): list of keys that are optional data variables (added as 1-d series of NaN if not in 'data')
        multidim_vars (optional): dictionary of variables with more than time dimension. Variable name as key, number of
            dimensions as values. This argument will be ignored as long as the variable is present in dataset
        time_vector (optional): :class:`numpy.ndarray` of :class:`numpy.datetime64` to take as time dimension for
            generating all-NaN datasets. This argument will be ignored as long as data is not None or empty
    Returns:
        :class:`xarray.Dataset`
    """

    # config for empty datasets or variables
    missing_val = np.nan
    if multidim_vars is None:
        multidim_vars = {}

    # init
    if vars_opt is None:
        vars_opt = []
    all_vars = vars + vars_opt

    # prepare for empty variables
    ndims_per_var = {var: 1 for var in dims + all_vars}
    for var, nd in multidim_vars.items():  # can grow larger than keys that shall be in output, only accessed by key
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


def merge_aux_data(mwr_data, all_data, srcs_to_ignore=None):
    """merge auxiliary data to time grid of microwave data

    Args:
        mwr_data: :class:`xarray.Dataset` of microwave radiometer data
        all_data: Dictionary of data from different sources (keys) as :class:`xarray.Dataset` (values). Can also contain
            the data in 'mwr_data' in which case it must be made sure the key is specified in 'srcs_to_ignore'
        srcs_to_ignore (optional): list of sources (keys) to ignore from 'all_data' e.g. because they are already
            contained in 'mwr_data'. Defaults to ['mwr', 'brt', 'blb']
    Returns:
        merged dataset of type :class:`xarray.Dataset`
    """

    if srcs_to_ignore is None:
        srcs_to_ignore = ['mwr', 'brt', 'blb']

    out = mwr_data
    for src in all_data:
        if src in srcs_to_ignore:
            continue

        # to make sure no variable is overwritten rename duplicates by suffixing it with its source
        for var in all_data[src]:
            if var in out:
                varname_map = {var: var + '_' + src}
                all_data[src] = all_data[src].rename(varname_map)

        # interp to same time grid (time grid from blb now stems from some interp) and merge into out
        srcdat_interp = all_data[src].interp(time=out['time'], method='nearest')  # nearest: flags stay integer
        out = out.merge(srcdat_interp, join='left')

    return out


def drop_duplicates(ds, dim):
    """drop duplicates from all data in ds for duplicates in dimension vector

    Args:
        ds: :class:`xarray.Dataset` or :class:`xarray.DataArray` containing the data
        dim: string indicating the dimension name to check for duplicates
    Returns:
        ds with unique dimension vector
    """

    _, ind = np.unique(ds[dim], return_index=True)  # keep first index but assume duplicate values identical anyway
    return ds.isel({dim: ind})


def scanflag_from_ele(ele, use_ele_diff=False):
    """infer scanflag (0: starring; 1: scanning) from elevation vector

    Args:
        ele: elevation vector as :class:`numpy.ndarray`
        use_ele_diff: if True infer scanflag from differences in ele, if False ele>89 are assumed starring, all others
            as scanning. Defaults to False.
    Returns:
        scanflags as :class:`numpy.ndarray` of same shape as ele
    """

    if use_ele_diff:
        err_msg = 'currently scanflags can only be inferred from assuming ele>89 as starring and all others as scanning'
        raise NotImplementedError(err_msg)
    else:
        return np.where(ele > 89, 0, 1)
