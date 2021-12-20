# -*- coding: utf-8 -*-
"""
Create E-PROFILE NetCDF from input dictionary or xarray Dataset
"""
from copy import deepcopy

import netCDF4 as nc
import xarray as xr

from mwr_raw2l1.errors import OutputDimensionError
from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.file_utils import get_conf


def write(data, filename, conf_file, *args, **kwargs):
    """wrapper picking the right writer according to the type of data"""

    if isinstance(data, dict):
        write_from_dict(data, filename, conf_file, *args, **kwargs)
    elif isinstance(data, xr.Dataset) or isinstance(data, xr.DataArray):
        write_from_xarray(data, filename, conf_file, *args, **kwargs)
    else:
        raise NotImplementedError('no writer for data of type ' + type(data))


def write_from_dict(data, filename, conf_file, format='NETCDF4'):
    """write data dictionary to NetCDF according to the format definition in conf_file by using the netCDF4 module"""
    conf = get_conf(conf_file)
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
    logger.info('data written to {}'.format(filename))


def write_from_xarray(data_in, filename, conf_file, format='NETCDF4', copy_data=False):
    """write data (Dataset) to NetCDF according to the format definition in conf_file by using the xarray module

    Args:
        data_in: xarray Dataset or DataArray containing data to write to file
        filename: name and path of output NetCDF file
        conf_file: yaml configuration file defining the format and contents of the output NetCDF file
        format: NetCDF format type of the output file. Default is NETCDF4
        copy_data (bool): In case of False, the dataset will experience in-place modifications which is suitable when
            the dataset is not used in its original form after calling the write function, for True a copy is modified.
            Defaults to False.
    """

    # value for _FillValue attribute of variables encoding field to have unset _FillValue in NetCDF
    enc_no_fillvalue = None  # tutorials from 2017 said False must be used, but with xarray 0.20.1 only None works

    conf = get_conf(conf_file)

    if copy_data:
        data = deepcopy(data_in)
    else:
        data = data_in

    # dimensions
    config_dims = conf['dimensions']['unlimited'] + conf['dimensions']['fixed']
    data.encoding.update(unlimited_dims=conf['dimensions']['unlimited'])  # acts during to_netcdf (default: fixed)

    for var, specs in conf['variables'].items():
        if var not in data.keys():
            if specs['optional']:
                # TODO: must create a variable of fill values only
                continue
            else:
                raise KeyError('Variable {} is a mandatory input but was not found in input dictionary'.format(var))

        # check dimensions (including order)
        if list(data[var].coords) != specs['dim']:
            raise OutputDimensionError('dimensions in data["{}"] ({}) do not match specs for output file ({})'.format(
                var, ', '.join(list(data[var].coords)), ', '.join(specs['dim'])))

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

    data.to_netcdf(filename, format=format)
    logger.info('data written to ' + filename)


def write_eprofile_netcdf_hardcode(filename, data):
    # TODO: This function can be removed once happy with the outcome of write()

    # configuration
    ncformat = 'NETCDF4'
    ncdateformat = 'seconds since 1970-01-01-00:00:00'
    # TODO: Consider transforming to DAYS since ... for consistency with other E-PROFILE data formats

    ncdims_unlimited = ['time']
    ncdims_fixed = ['frequency']
    ncvars = dict(
        time={'dim': ('time',), 'type': 'f8', '_FillValue': None, 'optional': False},
        frequency={'dim': ('frequency',), 'type': 'f4', '_FillValue': -999., 'optional': False},
        Tb={'dim': ('time', 'frequency'), 'type': 'f4', '_FillValue': -999., 'optional': False},
        dummyvar={'dim': ('time',), 'type': 'f4', '_FillValue': -999., 'optional': True},
    )
    ncvaratt = dict(
        time={'standard_name': 'time',
              'units': ncdateformat,
              'bounds': 'time_bounds',
              'comment': 'Time indication of samples is at the end of integration time'},
        frequency={'standard_name': 'sensor_band_spectral_radiation_frequency',
                   'units': 'GHz',
                   'bounds': 'time_bounds'},
        # TODO: check whether time bounds is correct here or whether it should be removed
        Tb={'standard_name': 'brightness_temperature',
            'units': 'K'},
        dummyvar={'comment': 'this is just a dummyvar for testing'},
    )

    # writer
    with nc.Dataset(filename, 'w', format=ncformat) as ncid:

        for dimact in ncdims_unlimited:
            ncid.createDimension(dimact, size=None)

        for dimact in ncdims_fixed:
            # print(dimact)
            # print(np.shape(data[dimact]))
            ncid.createDimension(dimact, size=len(data[dimact]))

        for var, specs in ncvars.items():
            ncvar = ncid.createVariable(var, specs['type'], specs['dim'], fill_value=specs['_FillValue'])
            ncvar.setncatts(ncvaratt[var])

            if var not in data.keys():
                if specs['optional']:
                    # TODO: check that this creates variable of righ size with only fill values
                    continue
                else:
                    raise KeyError('Variable {} is a mandatory input but was not found in input dictionary'.format(var))

            if var == 'time':
                ncvar[:] = nc.date2num(data[var], ncdateformat)
            else:
                ncvar[:] = data[var]
