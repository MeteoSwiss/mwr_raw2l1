import numpy as np
import xarray as xr

from mwr_raw2l1.errors import DimensionError, MissingInputArgument
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.scan_transform import scan_to_timeseries_from_aux


def attex_to_datasets(data_all, dims, vars, vars_opt):
    """generate unique :class:`xarray.Dataset` for each type of obs in 'data' using dimensions and variables specified

    Args:
        data_all: single instance of the read-in class (with observations in instance variable 'data') or as a list
             containing a series of instances of read-in classes.
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables
    Returns:
        a :class:`xarray.Dataset` containing the data
    """

    if not isinstance(data_all, list):  # accept also single instances of read-in class not inside a list
        data_all = [data_all]

    # add dim in second pos as Attex are single-channel instruments but frequency shall be present as 2nd
    for dat in data_all:
        if dat.data['Tb'].ndim == 2:
            dat.data['Tb'] = np.expand_dims(dat.data['Tb'], 1)

    return to_single_dataset([dat.data for dat in data_all], dims, vars, vars_opt)


def radiometrics_to_datasets(data_all, dims, vars, vars_opt):
    """generate unique :class:`xarray.Dataset` for each type of obs in 'data' using dimensions and variables specified

    Args:
        data_all: single instance of the read-in class (with observations in instance variable 'data') or as a list
             containing a series of instances of read-in classes.
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
        vars_opt: list of keys that are optional data variables
    Returns:
        dictionary with one :class:`xarray.Dataset` for each key. It contains one item for each key in data
    """

    if not isinstance(data_all, list):  # accept also single instances of read-in class not inside a list
        data_all = [data_all]

    out = {}
    sources = data_all[0].data.keys()
    for src in sources:
        out[src] = to_single_dataset([dat.data[src] for dat in data_all], dims[src], vars[src], vars_opt[src])
    return out


def rpg_to_datasets(data, dims, vars, vars_opt):
    """generate unique :class:`xarray.Dataset` for each type of obs in 'data' using dimensions and variables specified

    Args:
        data: dictionary containing the observations by type. Its keys correspond to the type of observations (e.g. brt,
            blb, irt ...). The observations themselves can be given as a single instance of the read-in class
            (with observations in variable 'data') or as a list containing a series of instances of read-in classes.
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

        if not data_series:  # fill in NaN variables if meas source does not exist (loop over empty data_series skipped)
            if src in ('brt', 'blb'):  # don't create empty datasets for missing MWR data
                continue
            logger.info('No {}-data available. Will generate a dataset fill values only for {}'.format(src, src))
            min_time = min([x.data['time'][0] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            max_time = max([x.data['time'][-1] for x in data['hkd']])  # class instances in data['hkd'] can be unordered
            out[src] = make_dataset(None, dims[src], vars[src], vars_opt[src],
                                    multidim_vars=multidim_vars, time_vector=[min_time, max_time])
            continue
        elif not isinstance(data_series, list):  # accept also single instances of read-in class not inside a list
            data_series = [data_series]
        out[src] = to_single_dataset([dat.data for dat in data_series], dims[src], vars[src], vars_opt[src],
                                     multidim_vars=multidim_vars)

    return out


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


def to_single_dataset(data_dicts, *args, **kwargs):
    """return a single :class:`xarray.Dataset` with unique time vector from a list of data dictionaries

    Args:
        data_dicts: list of data dictionaries to be concatenated to a time series
        *args: dimension and variable specifications passed on to :func:`make_dataset`
        **kwargs: dimension and variable specifications passed on to :func:`make_dataset`
    """
    datasets = []
    for dat in data_dicts:
        datasets.append(make_dataset(dat, *args, **kwargs))
    out = xr.concat(datasets, dim='time')  # merge all datasets of the same type
    out = drop_duplicates(out, dim='time')  # remove duplicate measurements
    return out


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


def merge_brt_blb(all_data):
    """merge brt (zenith MWR) and blb (scanning MWR) observations from an RPG instrument

    Args:
        all_data: dictionary with a :class:`xarray.Dataset` attached to each key (output of :func:`rpg_to_datasets`)
    """
    if 'brt' in all_data:
        out = all_data['brt']
    if 'blb' in all_data:
        if 'brt' in all_data:
            blb_ts = scan_to_timeseries_from_aux(all_data['blb'], hkd=all_data['hkd'], brt=all_data['brt'])
            out = out.merge(blb_ts, join='outer')
        else:
            out = scan_to_timeseries_from_aux(all_data['blb'], hkd=all_data['hkd'])

    return out
