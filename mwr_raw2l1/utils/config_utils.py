import yaml

from mwr_raw2l1.errors import MissingConfig, MWRConfigError
from mwr_raw2l1.utils.file_utils import abs_file_path


def get_conf(file):
    """get conf dictionary from yaml files. Don't do any checks on contents"""
    with open(file) as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf


def check_conf(conf, mandatory_keys, miss_description):
    """check for mandatory keys of conf dictionary

    if key is missing raises MissingConfig('xxx is a mandatory key ' + miss_description)
    """
    for key in mandatory_keys:
        if key not in conf:
            err_msg = ("'{}' is a mandatory key {}".format(key, miss_description))
            raise MissingConfig(err_msg)


def get_inst_config(file):
    """get configuration for each instrument and check for completeness of config file"""

    mandatory_keys = ['reader', 'meas_constructor', 'filename_scheme',
                      'input_directory', 'output_directory', 'base_filename_in', 'base_filename_out',
                      'station_latitude', 'station_longitude', 'station_altitude', 'nc_attributes']
    mandatory_ncattrs = ['wigos_station_id', 'instrument_id', 'site_location', 'institution', 'principal_investigator',
                         'instrument_manufacturer', 'instrument_model', 'instrument_generation', 'instrument_hw_id',
                         'instrument_calibration_status', 'date_of_last_absolute_calibration',
                         'type_of_automatic_calibrations']

    conf = get_conf(file)

    # verify conf dictionary structure
    check_conf(conf, mandatory_keys,
               'of instrument config files but is missing in {}'.format(file))
    check_conf(conf['nc_attributes'], mandatory_ncattrs,
               "of 'nc_attributes' in instrument config files but is missing in {}".format(file))
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

    # verify conf dictionary structure
    check_conf(conf, mandatory_keys,
               'of config files defining output NetCDF format but is missing in {}'.format(file))
    check_conf(conf['dimensions'], mandatory_dimension_keys,
               "of 'dimensions' config files defining output NetCDF format but is missing in {}".format(file))
    for varname, varval in conf['variables'].items():
        check_conf(varval, mandatory_variable_keys,
                   "of each variable in config files defining output NetCDF format but is missing for '{}' in {}"
                   .format(varname, file))
        if not isinstance(varval['dim'], list):
            raise MWRConfigError("The value attributed to 'dim' in variable '{}' is not a list in {}"
                                 .format(varname, file))

    return conf


def get_qc_config(file):
    """get configuration for quality control and check for completeness of config file"""

    mandatory_keys = ['Tb_threshold', 'delta_ele_sun', 'delta_azi_sun',
                      'check_missing_Tb', 'check_min_Tb', 'check_max_Tb',
                      'check_spectral_consistency', 'check_receiver_sanity',
                      'check_rain', 'check_sun', 'check_Tb_offset']

    conf = get_conf(file)
    check_conf(conf, mandatory_keys,
               'of quality control config files but is missing in {}'.format(file))

    return conf


def get_log_config(file):
    """get configuration for logger and check for completeness of config file"""

    mandatory_keys = ['logger_name', 'loglevel_stdout', 'write_logfile']
    mandatory_keys_file = ['logfile_path', 'logfile_basename', 'logfile_ext', 'logfile_timestamp_format',
                           'loglevel_file']

    conf = get_conf(file)
    check_conf(conf, mandatory_keys,
               'of log config files but is missing in {}'.format(file))
    if conf['write_logfile']:
        check_conf(conf, mandatory_keys_file,
                   "of log config files if 'write_logfile' is True, but is missing in {}".format(file))

    return conf


if __name__ == '__main__':
    get_inst_config(abs_file_path('mwr_raw2l1/config/config_0-20000-0-06610_A.yaml'))
    get_nc_format_config(abs_file_path('mwr_raw2l1/config/L1_format.yaml'))
    get_qc_config(abs_file_path('mwr_raw2l1/config/qc_config.yaml'))
    get_log_config(abs_file_path('mwr_raw2l1/config/log_config.yaml'))
