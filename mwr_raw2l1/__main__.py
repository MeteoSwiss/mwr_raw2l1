import argparse

import mwr_raw2l1
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.file_utils import abs_file_path, write_file_log


def main():
    """command line entry point for the mwr_raw2l1 package. Type 'python3 -m mwr_raw2l1 -h' for more info"""
    # instantiate parser
    parser = argparse.ArgumentParser(prog='python3 -m {}'.format(mwr_raw2l1.__name__),
                                     description='Transform MWR native files to (E-PROFILE) NetCDF format.')

    # add arguments
    parser.add_argument('conf_inst',
                        help='path to the instrument configuration file'
                             ' (absolute or relative to mwr_raw2l1 project dir'
                             ' (e.g. mwr_raw2l1/config/config_0-20000-0-06610_A.yaml))')
    parser.add_argument('--conf_nc',
                        help='path to the output NetCDF format configuration file'
                             ' (absolute or relative to mwr_raw2l1 project dir)')
    parser.add_argument('--conf_qc',
                        help='path to the configuration file specifying the quality control parameters'
                             ' (absolute or relative to mwr_raw2l1 project dir)')
    parser.add_argument('--time_start',
                        help='earliest timestamp (in filenames) of input files to be considered '
                             "(in form 'yyyymmddHHMM', 'yyyymmddHHMMSS', 'yyyymmdd' or similar)")
    parser.add_argument('--time_end',
                        help='latest timestamp (in filenames) of input files to be considered '
                             "(in form 'yyyymmddHHMM', 'yyyymmddHHMMSS', 'yyyymmdd' or similar)")
    parser.add_argument('--concat', action='store_true',
                        help='concatenate all timestamps in input directory matching search criteria'
                             ' to one single output file. Default is one output file per timestamp')
    parser.add_argument('--timestamp_src',
                        help="source of output file timestamp. Can be 'instamp_min'/'instamp_max' for using"
                             " smallest/largest timestamp of input filenames or 'time_min'/'time_max' for"
                             ' smallest/largest time in data.'
                             " Care for options 'instamp_min' or 'instamp_max': each file matching search pattern and"
                             ' having a timestamp is subject to provide the output timestamp even if the file is not of'
                             " a type readable by the package. Defaults to 'instamp_min'.")
    parser.add_argument('--log_files_success',
                        help='optional path where a list of all successfully processed files will be stored. Bunches'
                             ' processed together are separated by empty lines. Not necessarily each file in bunch has'
                             ' been processed (the ones not matching known extensions or suffixes are simply ignored)'
                             ' but none caused an error.')
    parser.add_argument('--log_files_fail',
                        help='optional path where a list of file bunches processed with errors will be stored. Bunches'
                             ' processed together are separated by empty lines. Often just one or a few files of each'
                             ' bunch cause an error (see log messages).')
    args = parser.parse_args()

    # interpret arguments and run mwr_raw2l1
    kwargs = {'inst_config_file': abs_file_path(args.conf_inst)}  # dict matching keyword of main.run with its value
    if args.conf_nc:
        kwargs['nc_format_config_file'] = args.conf_nc
    if args.conf_qc:
        kwargs['qc_config_file'] = args.conf_qc
    if args.time_start:
        kwargs['time_start'] = args.time_start
    if args.time_end:
        kwargs['time_end'] = args.time_end
    if args.concat:
        kwargs['concat'] = args.concat
    if args.timestamp_src:
        kwargs['timestamp_src'] = args.timestamp_src

    files_success, files_fail = run(**kwargs, halt_on_error=False)

    # write log of processed files if requested
    if args.log_files_success:
        write_file_log(args.log_files_success, files_success)
    if args.log_files_fail:
        write_file_log(args.log_files_fail, files_fail)


if __name__ == '__main__':
    main()
