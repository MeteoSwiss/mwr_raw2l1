# -*- coding: utf-8 -*-
"""
Create E-PROFILE NetCDF from input dictionary
"""
import netCDF4 as nc
import numpy as np
import yaml


def write(data, filename, config, format='NETCDF4'):
    with nc.Dataset(filename, 'w', format=format) as ncid:
        for dimact in config['dimensions']['unlimited']:
            ncid.createDimension(config['variables'][dimact]['name'], size=None)
        for dimact in config['dimensions']['fixed']:
            ncid.createDimension(config['variables'][dimact]['name'], size=len(data[dimact]))
        for var, specs in config['variables'].items():
            ncvar = ncid.createVariable(specs['name'], specs['type'], specs['dim'], fill_value=specs['FillValue'])
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


def read_config(file='L1_format.yaml'):
    with open(file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def write_eprofile_netcdf_hardcode(filename, data):
    # TODO: This function can be removed once happy wiht the outcome of write()

    # configuration
    ncformat = 'NETCDF4'
    ncdateformat = 'seconds since 1970-01-01-00:00:00'  # TODO: Transform to DAYS since ... for consistency with other E-PROFILE data formats

    ncdims_unlimited = ['time']
    ncdims_fixed = ['frequency']
    ncvars = dict(
        time={'dim': ('time',), 'type': 'f8', 'FillValue': None, 'optional': False},
        frequency={'dim': ('frequency',), 'type': 'f4', 'FillValue': -999., 'optional': False},
        Tb={'dim': ('time', 'frequency'), 'type': 'f4', 'FillValue': -999., 'optional': False},
        dummyvar={'dim': ('time',), 'type': 'f4', 'FillValue': -999., 'optional': True}
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
        dummyvar={'comment': 'this is just a dummyvar for testing'}
    )

    # writer
    with nc.Dataset(filename, 'w', format=ncformat) as ncid:

        for dimact in ncdims_unlimited:
            ncid.createDimension(dimact, size=None)

        for dimact in ncdims_fixed:
            print(dimact)
            print(np.shape(data[dimact]))
            ncid.createDimension(dimact, size=len(data[dimact]))

        for var, specs in ncvars.items():
            ncvar = ncid.createVariable(var, specs['type'], specs['dim'], fill_value=specs['FillValue'])
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


# testing the function
conf = read_config()
import reader_rpg

data = reader_rpg.brt
write_eprofile_netcdf_hardcode('nchardcode_test.nc', data)
write(data, 'ncyaml_test.nc', conf)
