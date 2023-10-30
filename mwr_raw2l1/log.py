import datetime as dt
import os
from logging import DEBUG, FileHandler, Formatter, StreamHandler, getLogger
from sys import stdout

from mwr_raw2l1.utils.config_utils import get_log_config
from mwr_raw2l1.utils.file_utils import abs_file_path


# get log config
log_config_file = abs_file_path('mwr_raw2l1/config/log_config.yaml')
conf = get_log_config(log_config_file)


# Colors for the log console output (Options see color_log-package)
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white'}

try:
    import colorlog  # import in own namespace to be explicit (getLogger is available from logging and colorlog)

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s [%(process)d] '
        '%(levelname)-8s %(message)s',
        datefmt=None,
        reset=True,
        log_colors=LOG_COLORS,
        secondary_log_colors={},
        style='%',
    )
    get_logger = colorlog.getLogger

except Exception as e:  # noqa E841
    #   print(e)
    get_logger = getLogger
    formatter = Formatter(
        '%(asctime)s [%(process)d] '
        '%(levelname)-8s %(message)s',
        '%Y-%m-%d %H:%M:%S',
    )


# general settings
logger = get_logger(conf['logger_name'])
logger.setLevel(DEBUG)  # set to the lowest possible level, using handler-specific levels for output


# logging to stdout
console_handler = StreamHandler(stdout)
console_formatter = formatter
console_handler.setFormatter(console_formatter)
console_handler.setLevel(conf['loglevel_stdout'])
logger.addHandler(console_handler)


# logging to file
if conf['write_logfile']:
    act_time_str = dt.datetime.now(tz=dt.timezone(dt.timedelta(0))).strftime(conf['logfile_timestamp_format'])
    log_filename = conf['logfile_basename'] + format(act_time_str) + conf['logfile_ext']
    log_file = str(abs_file_path(os.path.join(conf['logfile_path'], log_filename)))

    file_handler = FileHandler(log_file)
    file_handler_formatter = formatter
    file_handler.setFormatter(file_handler_formatter)
    file_handler.setLevel(conf['loglevel_file'])
    logger.addHandler(file_handler)
