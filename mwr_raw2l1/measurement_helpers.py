import numpy as np

from mwr_raw2l1.errors import DimensionError


def make_xr_dict(data, dims, vars):
    """generate a dictionary containing the dimensions and variables to initialise xarray dataset

    Args:
        data: dictionary containing the data
        dims: list of keys that are a dimension (must correspond to the order of dimensions in data)
        vars: list of keys that are data variables (dimensions don't need to be specified again)
    """

    out = {}
    for dim in dims:
        out[dim] = dict(dims=dim, data=data[dim])

    for var in vars:
        nd = np.ndim(data[var])
        if nd > len(dims):
            raise DimensionError("specified {} dimensions but data['{}'] is {}-dimensional".format(len(dims), var, nd))
        out[var] = dict(dims=dims[0:nd], data=data[var])
