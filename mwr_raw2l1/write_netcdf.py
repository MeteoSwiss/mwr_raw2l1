"""
Create NetCDF from :class:`xarray.Dataset` (or dictionary) according to specifications in the config file
"""
import datetime as dt
from copy import deepcopy

import netCDF4 as nc
import xarray as xr
from pkg_resources import get_distribution

import mwr_raw2l1
from mwr_raw2l1.errors import OutputDimensionError
from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config


def write(data, filename, nc_conf_file, inst_conf_file, *args, **kwargs):
    """wrapper picking the right writer according to the type of data"""

    logger.info('Starting writing to ' + filename)
    if isinstance(data, dict):
        write_from_dict(data, filename, nc_conf_file, inst_conf_file, *args, **kwargs)
    elif isinstance(data, xr.Dataset) or isinstance(data, xr.DataArray):
        write_from_xarray(data, filename, nc_conf_file, inst_conf_file, *args, **kwargs)
    else:
        raise NotImplementedError('no writer for data of type ' + type(data))


def write_from_xarray(data_in, filename, conf_nc, conf_inst, format='NETCDF4', copy_data=False):
    """write data (Dataset) to NetCDF according to the format definition in conf_file by using the :class:`xarray` module

    Args:
        data_in: :class:`xarray.Dataset` or :class:`DataArray` containing data to write to file
        filename: name and path of output NetCDF file
        conf_nc: configuration dict of yaml file defining the format and contents of the output NetCDF file
        conf_inst: configuration dict of yaml file with instrument specifications (contains global attrs for NetCDF)
        format: NetCDF format type of the output file. Default is NETCDF4
        copy_data (bool): In case of False, the dataset will experience in-place modifications which is suitable when
            the dataset is not used in its original form after calling the write function, for True a copy is modified.
            Defaults to False.
    """

    if copy_data:
        data = deepcopy(data_in)
    else:
        data = data_in

    # read in config file if config was not provided as dict
    if not isinstance(conf_nc, dict):
        conf_nc = get_nc_format_config(conf_nc)
    if not isinstance(conf_inst, dict):
        conf_inst = get_inst_config(conf_inst)

    # prepare data and add global attributes
    data = prepare_datavars(data, conf_nc)
    data = prepare_global_attrs(data, conf_nc, attr_key='attributes', set_history=False)  # only need history once
    data = prepare_global_attrs(data, conf_inst, attr_key='nc_attributes', set_history=True)

    data.to_netcdf(filename, format=format)
    logger.info('Data written to ' + filename)


def prepare_datavars(data, conf):
    """prepare data variables :class:`xarray.Dataset` for writing to file standard specified in 'conf'"""

    # value for _FillValue attribute of variables encoding field to have unset _FillValue in NetCDF
    enc_no_fillvalue = None  # tutorials from 2017 said False must be used, but with xarray 0.20.1 only None works

    # dimensions
    config_dims = conf['dimensions']['unlimited'] + conf['dimensions']['fixed']
    data.encoding.update(unlimited_dims=conf['dimensions']['unlimited'])  # acts during to_netcdf (default: fixed)
    for var, specs in conf['variables'].items():
        if var not in data.keys():
            if specs['optional']:
                # TODO: must create a variable of fill values only. Currently this is handled in Measurement constructor
                continue
            else:
                raise KeyError('Variable {} is a mandatory input but was not found in input dictionary'.format(var))

        # check dimensions (retain order of config specs, but order of coords returned by xarray Dataset is arbitrary)
        if sorted(list(data[var].coords)) != sorted(specs['dim']):
            # if last dim of specs is missing in data and scalar, add it to data (no need for subsequent check)
            if sorted(list(data[var].coords)) == sorted(specs['dim'][:-1]) \
                    and specs['dim'][-1] in data and len(data[specs['dim'][-1]]) == 1:
                newdim = specs['dim'][-1]
                tmp = data[var].expand_dims({newdim: 1}, axis=-1)
                data[var] = tmp.assign_coords({newdim: data[newdim]})
            else:
                err_msg = "dimensions in data['{}'] (['{}']) do not match specs for output file (['{}'])".format(
                    var, "', '".join(list(data[var].coords)), "', '".join(specs['dim']))
                raise OutputDimensionError(err_msg)

        # set all attributes and datatype
        data[var].attrs.update(specs['attributes'])
        data[var].encoding.update(dtype=specs['type'])

        # set fill value
        if var in config_dims:
            data[var].encoding.update(_FillValue=enc_no_fillvalue)  # no fill value for dimensions (CF-compliance)
        else:
            data[var] = data[var].fillna(specs['_FillValue'])
            data[var].encoding.update(_FillValue=specs['_FillValue'])

    # workaround for setting units and calendar of time variable (use encoding instead of attrs)
    encs = {}
    for att in ['units', 'calendar']:
        encs[att] = data['time'].attrs.pop(att)
    data['time'].encoding.update(encs)

    # remove undesired variables and dimensions from data (all that are not in the config file)
    vars_to_drop = []
    for var in data.variables:
        if var not in conf['variables']:
            vars_to_drop.append(var)
    data = data.drop_vars(vars_to_drop)
    dims_to_drop = []
    for var in data.dims:
        if var not in config_dims:
            dims_to_drop.append(var)
    data = data.drop_dims(dims_to_drop)

    # set variable and dimension names to the ones wished for output (CARE: must be last operation before save!!!)
    varname_map = {var: specs['name'] for var, specs in conf['variables'].items()}
    data = data.rename(varname_map)
    renamed_unlim_dim = [varname_map[dim] for dim in data.encoding['unlimited_dims']]
    data.encoding['unlimited_dims'] = renamed_unlim_dim

    return data


def prepare_global_attrs(data, conf, attr_key, set_history=True):
    """add global attributes from configuration dictionary

    Args:
        data: :class:`xarray.Dataset`
        conf: configuration dictionary with global attributes under the key given by attr_key
        attr_key: string specifying the key under which attributes are stored in conf dict. Usually 'attributes' or
            'nc_attributes'
        set_history: add history attribute specifying when and how file was generated. Defaults to True.
    """
    for attname, attval in conf[attr_key].items():
        data.attrs[attname] = attval

    if set_history:
        data.attrs['history'] = generate_history_str()

    return data


def generate_history_str():
    current_time = dt.datetime.now(tz=dt.timezone(dt.timedelta(0)))
    proj_dir = mwr_raw2l1.__file__.split('/')[-2]
    proj_dist = get_distribution(proj_dir)
    return '{}: {} ({})'.format(current_time.strftime('%Y%m%d'), proj_dist.project_name, proj_dist.version)


def write_from_dict(data, filename, nc_conf_file, inst_conf_file=None, format='NETCDF4'):
    """write data dictionary to NetCDF according to the format definition in conf_file by using the netCDF4 module

    CARE: This is a legacy function here for completeness but not maintained any further.
          Especially, writing of global attributes is not yet included.
    """

    logger.warning('This function is not maintained any further and comes with no guarantee at all. Consider using '
                   'write_from_xarray instead.')
    conf = get_nc_format_config(nc_conf_file)
    with nc.Dataset(filename, 'w', format=format) as ncid:
        for dimact in conf['dimensions']['unlimited']:
            ncid.createDimension(conf['variables'][dimact]['name'], size=None)
        for dimact in conf['dimensions']['fixed']:
            ncid.createDimension(conf['variables'][dimact]['name'], size=len(data[dimact]))
        for var, specs in conf['variables'].items():
            ncvar = ncid.createVariable(specs['name'], specs['type'], specs['dim'], fill_value=specs['_FillValue'])
            ncvar.setncatts(specs['attributes'])
            if var not in data.keys():
                if specs['optional']:
                    # TODO: check that this creates variable of right size with only fill values
                    continue
                else:
                    raise KeyError('Variable {} is a mandatory input but was not found in input dictionary'.format(var))
            if var == 'time':
                ncvar[:] = nc.date2num(data[var], specs['attributes']['units'])
            else:
                ncvar[:] = data[var]
    logger.info('Data written to {}'.format(filename))
