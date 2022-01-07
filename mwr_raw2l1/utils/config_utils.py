import yaml

from mwr_raw2l1.errors import MissingConfig, MWRConfigError
from mwr_raw2l1.utils.file_utils import abs_file_path


def get_conf(file):
    """conf get dictionary from yaml files. Don't do any checks on contents"""
    with open(file) as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf


def get_inst_config(file):
    """get configuration for each instrument and check for completeness of config file"""

    mandatory_keys = ['station_latitude', 'station_longitude', 'station_altitude', 'nc_attributes']
    mandatory_ncattrs = ['wigos_station_id', 'instrument_id', 'site_location', 'institution', 'principal_investigator',
                         'instrument_manufacturer', 'instrument_model', 'instrument_generation', 'instrument_hw_id',
                         'instrument_calibration_status', 'date_of_last_absolute_calibration',
                         'type_of_automatic_calibrations']

    conf = get_conf(file)

    # verify configuration file is complete
    for key in mandatory_keys:
        if key not in conf:
            err_msg = "'{}' is a mandatory key in instrument config files but is missing in {}".format(key, file)
            raise MissingConfig(err_msg)
    for attname in mandatory_ncattrs:
        if attname not in conf['nc_attributes']:
            err_msg = ("'{}' is a mandatory global attribute under 'nc_attributes' in instrument config files "
                       'but is missing in {}'.format(attname, file))
            raise MissingConfig(err_msg)
    for attname, attval in conf['nc_attributes'].items():
        if attname[:5].lower() == 'date_' and not isinstance(attval, str):
            raise MWRConfigError('Dates for global attrs must be given as str. Not the case for ' + attname)

    return conf


def get_nc_format_config(file):
    """get configuration for output NetCDF format and check for completeness of config file"""

    mandatory_keys = ['dimensions', 'variables', 'attributes']
    mandatory_variable_keys = ['name', 'dim', 'type', '_FillValue', 'optional', 'attributes']
    mandatory_dimension_keys = ['unlimited', 'fixed']

    conf = get_conf(file)

    # verify configuration file is complete
    for key in mandatory_keys:
        if key not in conf:
            err_msg = ("'{}' is a mandatory key in config files defining output NetCDF format "
                       'but is missing in {}'.format(key, file))
            raise MissingConfig(err_msg)
    for dimkey in mandatory_dimension_keys:
        if dimkey not in conf['dimensions']:
            err_msg = ("'{}' is a mandatory key to 'dimensions' in config files defining output NetCDF format "
                       'but is missing in {}'.format(dimkey, file))
            raise MissingConfig(err_msg)
    for varname, varval in conf['variables'].items():
        for varkey in mandatory_variable_keys:
            if varkey not in varval:
                err_msg = ("'{}' is a mandatory key to each variable in config files defining output NetCDF format "
                           "but is missing for '{}' in {}".format(varkey, varname, file))
                raise MissingConfig(err_msg)
        if not isinstance(varval['dim'], list):
            raise MWRConfigError("The value attributed to 'dim' in variable '{}' is not a list in {}"
                                 .format(varname, file))

    return conf


if __name__ == '__main__':
    get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
    get_nc_format_config(abs_file_path('mwr_raw2l1/config/L1_format.yaml'))
