import argparse

import mwr_raw2l1
from mwr_raw2l1.main import run
from mwr_raw2l1.utils.file_utils import abs_file_path


def main():
    """command line entry point for the mwr_raw2l1 package. Type 'python3 -m mwr_raw2l1 -h' for more info"""
    # instantiate parser
    parser = argparse.ArgumentParser(prog='python3 -m {}'.format(mwr_raw2l1.__name__),
                                     description='Transform MWR native files to (E-PROFILE) NetCDF format.')

    # add arguments
    parser.add_argument('conf_inst',
                        help='path to the instrument configuration file'
                             ' (absolute or relative to mwr_raw2l1 project dir)')
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

    run(**kwargs, halt_on_error=False)


if __name__ == '__main__':
    main()
