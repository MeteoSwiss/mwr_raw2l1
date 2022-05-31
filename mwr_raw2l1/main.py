import os.path

from mwr_raw2l1.errors import MWRConfigError
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.readers.reader_attex import read_multiple_files as reader_attex  # noqa: F401
from mwr_raw2l1.readers.reader_radiometrics import read_multiple_files as reader_radiometrics  # noqa: F401
from mwr_raw2l1.readers.reader_rpg import read_multiple_files as reader_rpg  # noqa: F401
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config, get_qc_config
from mwr_raw2l1.utils.file_utils import abs_file_path, generate_output_filename, get_files, group_files
from mwr_raw2l1.write_netcdf import Writer


def run(inst_config_file, nc_format_config_file, qc_config_file, concat=False, halt_on_error=True, **kwargs):
    """main function reading in raw files, generating and processing measurement instance and writing output file

    Args:
        inst_config_file: yaml configuration file for the instrument to process
        nc_format_config_file: yaml configuration file defining the output NetCDF format
        qc_config_file: yaml configuration file specifying the quality control parameters
        concat (optional): concatenate data to single output file instead of generating an output for each timestamp.
            Defaults to False.
        halt_on_error: stop execution if an error is encountered. If False the error will be logged while the function
            continues with the next bunch of files. Defaults to True.
        **kwargs: Keyword arguments passed over to get_files function, typically 'time_start' and 'time_end'
    """

    logger.info('Running main routine for ' + inst_config_file)

    # prepare
    # -------
    conf_inst = get_inst_config(inst_config_file)
    conf_nc = get_nc_format_config(nc_format_config_file)
    conf_qc = get_qc_config(qc_config_file)

    reader = get_reader(conf_inst['reader'])
    meas_constructor = get_meas_constructor(conf_inst['meas_constructor'])

    all_files = get_files(abs_file_path(conf_inst['input_directory']), conf_inst['base_filename_in'], **kwargs)
    if not all_files:
        logger.info('No files matching pattern {} in {}. Main routine returns without action.'.format(
            conf_inst['base_filename_in'], conf_inst['input_directory']))
        return
    if concat:
        file_bunches = [all_files]
    else:
        file_bunches = group_files(all_files, conf_inst['filename_scheme'])

    # process
    # -------
    error_seen = False
    for files in file_bunches:
        if halt_on_error:
            process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc)
        else:
            try:
                process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc)
            except Exception as e:
                error_seen = True
                logger.error('Error while processing {}'.format([os.path.basename(f) for f in files]))
                logger.exception(e)

    if error_seen:
        logger.error('Main routine terminated with errors (see above)')
    else:
        logger.info('Main routine terminated successfully')


def process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc):
    """process the input files with indicated reader, meas_constructor and conf dictionaries.

    All input files will be concatenated to one output file
    """

    # read and interpret data
    # -----------------------
    all_data = reader(files)
    meas = meas_constructor(all_data, conf_inst)
    meas.run(conf_qc)

    # write output
    # ------------
    outfile = generate_output_filename(conf_inst['base_filename_out'], meas.data['time'])
    outfile_with_path = os.path.join(abs_file_path(conf_inst['output_directory']), outfile)
    nc_writer = Writer(meas.data, outfile_with_path, conf_nc, conf_inst)
    nc_writer.run()


def get_reader(name):
    """get data reader from string

    Args:
        name: name of the reader as string. Known readers are reader_attex, reader_radiometrics and reader_rpg
    """
    try:
        reader = globals()[name]  # need globals() here, not locals()
    except KeyError:
        raise MWRConfigError("The reader '{}' specified in the config file is unknown to {}".format(name, __file__))
    return reader


def get_meas_constructor(name):
    """get constructor method for Measurement class from string

    Args:
        name: name of the constuctor as string. Known constructors are from_attex, from_radiometrics and from_rpg"""
    try:
        meas_constructor = getattr(Measurement, name)
    except AttributeError:
        raise MWRConfigError("The measurement constructor '{}' specified in the config file is not defined in the "
                             'Measurement class'.format(name))
    return meas_constructor


if __name__ == '__main__':
    run('config/config_0-20000-0-99999_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # Attex
    run('config/config_0-20000-0-10393_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # Radiometrics
    run('config/config_0-20000-0-06610_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # RPG HATPRO
