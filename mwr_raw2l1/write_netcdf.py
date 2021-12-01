# -*- coding: utf-8 -*-
"""
Create E-PROFILE NetCDF from input dictionary
"""
import netCDF4 as nc
import numpy as np

from mwr_raw2l1.utils.file_utils import get_conf


def write(data, filename, conf_file, format='NETCDF4'):
    conf = get_conf(conf_file)
    with nc.Dataset(filename, 'w', format=format) as ncid:
        for dimact in conf['dimensions']['unlimited']:
            ncid.createDimension(conf['variables'][dimact]['name'], size=None)
        for dimact in conf['dimensions']['fixed']:
            ncid.createDimension(conf['variables'][dimact]['name'], size=len(data[dimact]))
        for var, specs in conf['variables'].items():
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
    print('data written to {}'.format(filename))


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
if __name__ == '__main__':
    from legacy_reader_rpg import read_brt

    data = read_brt('data/rpg/C00-V859_190803.BRT')
    write_eprofile_netcdf_hardcode('nchardcode_test.nc', data)
    write(data, 'ncyaml_test.nc', 'L1_format.yaml')
