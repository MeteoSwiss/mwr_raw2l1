import os.path

from mwr_raw2l1.errors import MWRConfigError
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config
from mwr_raw2l1.utils.file_utils import generate_output_filename, get_files
from mwr_raw2l1.write_netcdf import Writer
# --------------------------------------------------------------------------------------------- # noqa: F401, I001, I004
# import readers for different instrument types                                                 # noqa: F401, I001, I004
from mwr_raw2l1.readers.reader_attex import read_multiple_files as reader_attex                 # noqa: F401, I001, I004
from mwr_raw2l1.readers.reader_radiometrics import read_multiple_files as reader_radiometrics   # noqa: F401, I001, I004
from mwr_raw2l1.readers.reader_rpg import read_multiple_files as reader_rpg                     # noqa: F401, I001, I004


def main(inst_config_file, nc_format_config_file, **kwargs):
    """main function reading in raw files, generating and processing measurement instance and writing output file

    Args:
        inst_config_file: yaml configuration file for the instrument to process
        nc_format_config_file: yaml configuration file defining the output NetCDF format
        **kwargs: Keyword arguments passed over to get_files function, typically 'time_start' and 'time_end'
    """

    logger.info('Running main function for ' + inst_config_file)

    # prepare
    # -------
    conf_inst = get_inst_config(inst_config_file)
    conf_nc = get_nc_format_config(nc_format_config_file)

    reader = get_reader(conf_inst['reader'])
    meas_constructor = get_meas_constructor(conf_inst['meas_constructor'])

    files = get_files(conf_inst['input_directory'], conf_inst['base_filename_in'], **kwargs)
    if not files:
        logger.info('No files matching pattern {} in {}. Main functions returns without action.'.format(
            conf_inst['base_filename_in'], conf_inst['input_directory']))
        return

    # read and interpret data
    # -----------------------
    all_data = reader(files)
    meas = meas_constructor(all_data)
    meas.run(conf_inst)

    # write output
    # ------------
    outfile = generate_output_filename(conf_inst['base_filename_out'], meas.data['time'])
    outfile_with_path = os.path.join(conf_inst['output_directory'], outfile)
    nc_writer = Writer(meas.data, outfile_with_path, conf_nc, conf_inst)
    nc_writer.run()

    logger.info('Main function terminated successfully')


def get_reader(name):
    """get data reader from name string"""
    try:
        reader = globals()[name]  # need globals() here, not locals()
    except KeyError:
        raise MWRConfigError("The reader '{}' specified in the config file is unknown to {}".format(name, __file__))
    return reader


def get_meas_constructor(name):
    """get constructor method for measurement class from name string"""
    try:
        meas_constructor = getattr(Measurement, name)
    except AttributeError:
        raise MWRConfigError("The measurement constructor '{}' specified in the config file is not defined in the "
                             'Measurement class'.format(name))
    return meas_constructor


if __name__ == '__main__':
    main('config/config_0-20000-0-99999_A.yaml', 'config/L1_format.yaml')  # Attex
    main('config/config_0-20000-0-10393_A.yaml', 'config/L1_format.yaml')  # Radiometrics MP3000
    main('config/config_0-20000-0-06610_A.yaml', 'config/L1_format.yaml')  # RPG HATPRO

