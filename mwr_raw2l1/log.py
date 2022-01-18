import datetime as dt
from logging import INFO, FileHandler, Formatter, StreamHandler, getLogger
from sys import stdout

from mwr_raw2l1.utils.file_utils import abs_file_path

# define log file name and path
act_time_str = dt.datetime.now().strftime('%Y%m%d%H%M%S')
log_file = str(abs_file_path('mwr_raw2l1/logs/log_{}.txt'.format(act_time_str)))

# Colors for the log console output (Options see color_log-package)
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white'}

try:
    import colorlog
    from colorlog import ColoredFormatter

    formatter = ColoredFormatter(
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

logger = get_logger('mwr_raw2l1')
logger.setLevel(INFO)

console_handler = StreamHandler(stdout)
console_formatter = formatter
console_handler.setFormatter(console_formatter)
console_handler.setLevel(INFO)
logger.addHandler(console_handler)

# if not os.path.exists(self.cfg.LOG_PATH):
#     self.error(ERROR, """Log file directory "{path}" does not exists""".format(path=self.cfg.LOG_PATH))
#     dir_not_found_hint(self.cfg.LOG_PATH)
#     raise LogPathNotExists


file_handler = FileHandler(log_file)
file_handler_formatter = formatter
file_handler.setFormatter(file_handler_formatter)
file_handler.setLevel(INFO)
logger.addHandler(file_handler)
