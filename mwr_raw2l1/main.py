import os.path
import warnings

from mwr_raw2l1.errors import MWRConfigError
from mwr_raw2l1.log import logger
from mwr_raw2l1.measurement.measurement import Measurement
from mwr_raw2l1.readers.reader_attex import read_multiple_files as reader_attex  # noqa: F401
from mwr_raw2l1.readers.reader_radiometrics import read_multiple_files as reader_radiometrics  # noqa: F401
from mwr_raw2l1.readers.reader_rpg import read_multiple_files as reader_rpg  # noqa: F401
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config, get_qc_config
from mwr_raw2l1.utils.file_utils import abs_file_path, generate_output_filename, get_files, group_files
from mwr_raw2l1.write_netcdf import Writer


# omit FutureWarnings from xarray (these can be caused xarray-internal implementations on py 3.9)
warnings.filterwarnings(action='ignore', category=FutureWarning, module='xarray')


def run(inst_config_file, nc_format_config_file=None, qc_config_file=None, concat=False, halt_on_error=True,
        timestamp_src='instamp_min', **kwargs):
    """main function reading in raw files, generating and processing measurement instance and writing output file

    Args:
        inst_config_file: yaml configuration file for the instrument to process
        nc_format_config_file (optional): yaml configuration file defining the output NetCDF format.
            Defaults to the E-PROFILE file standard defined in mwr_raw2l1/config/L1_format.yaml
        qc_config_file (optional): yaml configuration file specifying the quality control parameters
        concat (optional): concatenate data to single output file instead of generating an output for each timestamp.
            Defaults to False.
        halt_on_error (optional): stop execution if an error is encountered. If False the error will be logged while the
            function continues with the next bunch of files. Defaults to True.
        timestamp_src (optional): source of output file timestamp. Can be 'instamp_min'/'instamp_max' for using
            smallest/largest timestamp of input filenames or 'time_min'/'time_max' for smallest/largest time in data.
            Care for instamp options: each file matching search pattern and having a timestamp is subject to provide the
            output timestamp even if the file is not of a type readable by the package. Defaults to 'instamp_min'.
        **kwargs: Keyword arguments passed over to :func:`get_files`, typically 'time_start' and 'time_end'

    Returns:
        files_success: list of file bunches with successful processing. Not necessarily each file in bunch has been
            processed (the ones not matching known extensions or suffixes are simply ignored) but none caused an error.
        files_fail: list of file bunches which caused an error in processing. Often just one or a few files of each
            bunch cause an error (see log messages).
    """

    logger.info('Running main routine for {}'.format(inst_config_file))
    if concat:
        logger.info('Concatenation of multiple timestamps to single output file enabled')

    # complete input
    # --------------
    if nc_format_config_file is None:
        nc_format_config_file = abs_file_path('mwr_raw2l1/config/L1_format.yaml')
    if qc_config_file is None:
        qc_config_file = abs_file_path('mwr_raw2l1/config/qc_config.yaml')

    # prepare
    # -------
    conf_inst = get_inst_config(inst_config_file)
    conf_nc = get_nc_format_config(nc_format_config_file)
    conf_qc = get_qc_config(qc_config_file)
    try:
        if conf_inst['lwcl_check'] and 'do_check' in conf_inst['lwcl_check']:
            logger.info('Liquid cloud check activated for this instrument.')
            conf_qc['lwcl_check'] = conf_inst['lwcl_check']['do_check']
            conf_qc['lwcl_multiplying_factor'] = conf_inst['lwcl_check']['multiplying_factor']
    except KeyError:
        conf_qc['lwcl_check'] = False
        conf_qc['lwcl_multiplying_factor'] = None
        logger.info('No liquid cloud check configured in instrument config file.')

    reader = get_reader(conf_inst['reader'])
    meas_constructor = get_meas_constructor(conf_inst['meas_constructor'])

    files_success = []
    files_fail = []
    all_files = get_files(abs_file_path(conf_inst['input_directory']), conf_inst['base_filename_in'], **kwargs)
    if not all_files:
        logger.info('No files matching pattern {} in {} (in the specified time interval).'
                    ' Main routine returns without action.'.format(
                        conf_inst['base_filename_in'], conf_inst['input_directory']))
        return files_success, files_fail
    if concat:
        file_bunches = [all_files]
    else:
        file_bunches = group_files(all_files, conf_inst['filename_scheme'])

    # process
    # -------
    error_seen = False
    for files in file_bunches:
        if halt_on_error:
            process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc, timestamp_src)
            files_success.append(files)
        else:
            try:
                process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc, timestamp_src)
                files_success.append(files)
            except Exception as e:  # noqa B902
                error_seen = True
                logger.error('Error while processing {}'.format([os.path.basename(f) for f in files]))
                logger.exception(e)
                files_fail.append(files)

    if error_seen:
        logger.error('Main routine terminated with errors (see above)')
    else:
        logger.info('Main routine terminated successfully')

    return files_success, files_fail


def process_files(files, reader, meas_constructor, conf_inst, conf_qc, conf_nc, output_timestamp_style):
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
    outfile = generate_output_filename(conf_inst['base_filename_out'], output_timestamp_style,
                                       files_in=files, time=meas.data['time'])
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
    fs, ff = run('config/config_0-20000-0-06610_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # RPG HATPRO

    run('config/config_0-20000-0-06620_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # RPG TEMPRO
    run('config/config_0-20008-0-IZO_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml')  # RPG LHATPRO

    # For generating reference output file for test_rpg and testing concat option:
    # run('config/config_0-20000-0-06610_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml', concat=True)  # RPG
    # run('config/config_0-20000-0-06620_A.yaml', 'config/L1_format.yaml', 'config/qc_config.yaml', concat=True)  # RPG

    # For testing with offline data
    # run('../offline/radiometrics_lin_nodata_csv/config_lin.yaml')
    # run('../offline/radiometrics_lin_scan/config_lin.yaml')
    # run('../offline/radiometrics_lin_nonint_rectype/config_lin.yaml', halt_on_error=False)
    # run('../offline/rpg_lhatpro/config_izo.yaml')
    # run('../offline/inoe/config_inoe.yaml')
    # run('../offline/sha_tempro/config_MWR_SHA_A_ed.yaml')
    # run('../offline/rpg_single_obs_blb/config_PAY_A_ed.yaml')

    pass
