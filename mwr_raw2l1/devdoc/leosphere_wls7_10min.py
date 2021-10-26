    #!/usr/bin/env python
    # -*- encoding: utf-8 -*-

    from __future__ import print_function
    from __future__ import division
    from __future__ import absolute_import

    import sys
    import os
    import re
    import ast
    import datetime as dt

    import numpy as np

class WLS7_10(WLS7):
    MODEL = 'WLS7 1 sec'






for file_path in file_paths:
        instrument = BaseInstrument(file_path)

        try:
            self.read_file()
        except FileNotExist:
            pass

        try:
            self.preprocess()
        except NaN:
            pass

        try:
            self.calibrate()
        except NoConvergence:


        self.calculate()
        self.store()


    except ZeorDevision:
        pass



file_path = 'huhu.nc'
read_file()

file_path = 'huhu2.nc'
read_file()


inst1 = BaseInstrument('huhu.nc')
inst2 = BaseInstrument('huhu2.nc')

inst2.read_file()
inst1.read_file()



def read_file():
    in_file = open(file_path)




class BaseInstrument():

    def __init__(self, file_path):
        self.file_path = file_path

    def read_file(self):
        while True:
            try:
                self.in_file = open(self.filepath)

            except IOError :
                if IOError.temporär():
                    sleep(10)
                    continue
                else:
                    self.logger.critical('cannot open file {}'.format(self.filepath))
                    raise FileNotExist

#        return infile

    def preprocess(self):
        pass

    def preprocess2(self):
        pass

    def calibrate(self):
        pass

    def calculate(self):
        self.in_file.close()
        del self.in_file

    def store(self):
        pass


class Fourier():

    def __init__(self):
        pass

    def calculate(self, in_data):
        return np.forier(self.in_data)


in_data = [ökjgölfgjä]

fourier = Fourier()
spect = fourier.calculate(in_data)

kljgölgfjdö
fdjfdölfgö






class WLS7(Base_Instrument):

    def preprocess(self):

class WLS8(Base_Instrument):

    def preprocess(self):

    def preprocess2(self):
        # tue noch mehr



    class WLS7(Base_Instrument):


    def preprocess(self):
        print('preprocessing {}'.fomrat(self.BRAND))



    # brand and model of the LIDAR
    BRAND = 'leosphere'
    MODEL = 'WLS7 10 min'

    # CONSTANTS
    MIN_2_SEC = 60

    FILE_SEP = '\t'

    # date format
    DATE_FMT = ['%Y/%m/%d %H:%M']

    HEADER_TAG = 'HeaderSize'
    HEADER_CHAR_VALUE = '='
    HEADER_BAD_CHAR_RE = r'[()\[\]\/°%]'
    # header value with special processing
    HEADER_SPECIAL = [
        'GPS Localisation',
        'GPS Location',
        'Altitudes (m)',
    ]

    LOCALIZATION_DELIMS = r':|N|E|°|\xb0C'

    RAW_DATA_MISSING = ['NaN']

    # possible name of time var
    VAR_TIME = ['Timestamp_end_of_interval']

    VAR_1D = [
        ('wiper_count', ['Wiper_count']),
        ('temp_int', ['Int_Temp_(°C)', 'Int_Temp_\xb0C']),
        ('temp_ext', ['Ext_Temp_(°C)', 'Ext_Temp_\xb0C']),
        ('pres', ['Pressure_(hPa)', 'Pressure_hPa']),
        ('rh', ['Rel_Humidity_(%)', 'Rel_Humidity_']),
    ]
    # variables which need to be merged
    VAR_2D = [
        ('ws_disp', ['Wind_Speed_Dispersion']),
        ('ws_max', ['Wind_Speed_max']),
        ('ws_min', ['Wind_Speed_min']),
        ('ws', ['Wind_Speed']),
        ('wd', ['Wind_Direction']),
        ('w_disp', ['Zwind_Dispersion']),
        ('w', ['Zwind']),
        ('cnr_min', ['CNR_min']),
        ('cnr', ['CNR']),
        ('doppler_speed', ['Dopp_Spect_Broad']),
        ('data_availability', ['Data_Availability']),
    ]


    def merge_structured_arrays(list_arr):
        """merge structure array
        based on https://gist.github.com/astrofrog/2552867
        """

        # if list has only one element return array
        if len(list_arr) == 1:
            return list_arr[0]

        final = list_arr[0].copy()

        for arr in list_arr[1:]:

            final_size = final.size
            arr_size = arr.size
            final.resize(final_size + arr_size)
            final[final_size:] = arr

        return final

    def convert_time_str(str_):
        """convert date time string into datetime object"""

        for fmt in DATE_FMT:
            try:
                date = dt.datetime.strptime(str_, fmt)
                return date
            except ValueError:
                continue

        return None

    def norm_value_name(name):
        """normalize name of values"""

        # remove multiple blank and replace by one
        name = re.sub(r'\s+', ' ', name).strip()
        # remove unwanted caracters in name
        name = re.sub(HEADER_BAD_CHAR_RE, '', name)
        # capitalize first letter of words
        if ' ' in name:
            name = name.title()
        # remove all blank
        name = re.sub(r'\s+', '', name)

        return name


    def get_localization(value_str, conf, logger):
        """extract latitude and longitude"""

        logger.debug('try parsing {}'.format(value_str))

        # check if value available
        if len(value_str) == 0 or len(value_str) == 'Not Available':
            logger.warning('localization data unavailable')
            lat = conf['missing_float']
            lon = conf['missing_float']
            return lat, lon

        # we have to parse the line
        tmp = re.split(LOCALIZATION_DELIMS, value_str)
        try:
            lat = float(tmp[1])
        except ValueError:
            lat = float(tmp[1][:-1])
        finally:
            lat = conf['missing_float']

        try:
            lon = float(tmp[3])
        except ValueError:
            lon = float(tmp[3][:-1])
        finally:
            lon = conf['missing_float']

        return lat, lon


    def get_altitude(value_str, logger):
        """extract list of alitudes"""

        alt = [float(val) for val in value_str.split()]

        logger.debug('list of altitudes: {}'.format(alt))

        return np.array(alt)


    def read_file(file_, logger):
        """read one file and return a list without newline character"""

        logger.debug('reading {}'.format(os.path.basename(file_)))
        with open(file_, 'r') as f_id:
            raw_lines = f_id.readlines()

        # remove end of line character
        raw_lines = [line.strip() for line in raw_lines]

        return raw_lines


    def get_header_size(lines, logger):
        """Extract value from header by identifying line with equal sign"""

        header_found = False
        for line in lines:
            # search for header marker
            if HEADER_TAG in line:
                header_found = True
                header_size = int(line.split('=')[1])
                logger.debug('size of header {}'.format(header_size))

                return header_size

        if not header_found:
            return None


    def read_header_data(file_, conf, data, logger):
        """read data store in the header"""

        # read file
        raw_lines = read_file(file_, logger)
        header_size = get_header_size(raw_lines, logger)
        if header_size is None:
            logger.critical("impossible to file header size. stopping reading")
            sys.exit(1)

        # automatically extract data from header
        for i_line in range(header_size):
            # we only want line with =
            if HEADER_CHAR_VALUE not in raw_lines[i_line]:
                continue

            # split name and value to process it
            value_name, value = raw_lines[i_line].split(HEADER_CHAR_VALUE)

            # case value contain ')'
            if ')' in value:
                logger.debug('unwanted parenthesis in {} {}'.format(value_name, value))
                value = re.sub(r'\)', '', value)

            # special variable
            if value_name in HEADER_SPECIAL:

                if value_name == 'GPS Localisation' or value_name == 'GPS Location':
                    data['latitude'], data['longitude'] = get_localization(value,
                                                                           conf, logger)
                if value_name == 'Altitudes (m)':
                    data['range'] = get_altitude(value, logger)

                continue

            # others variables. clean name et convert value
            logger.debug('try parsing {} {}'.format(value_name, value))
            value_name = norm_value_name(value_name)
            try:
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass
            data[value_name] = value

        return data


    def read_columns(file_, data, conf, logger):
        """read the data store as columns """

        header = data['HeaderSize']

        # get the number of columns to fix types
        with open(file_) as f_id:
            count = 0
            while count <= header + 1:
                line = f_id.readline()
                count += 1

        col_names = [col for col in line.strip().split(FILE_SEP)]
        col_dtypes = [np.float] * (len(col_names) - 1)
        col_dtypes = [dt.datetime] + col_dtypes

        logger.debug('reading columns')

        columns = np.genfromtxt(
            file_,
            skip_header=header + 2,
            delimiter=FILE_SEP,
            missing_values=RAW_DATA_MISSING,
            filling_values=conf['missing_float'],
            names=col_names,
            dtype=col_dtypes,
            converters={0: convert_time_str},
            invalid_raise=False,
        )

        return columns


    def create_1d_var(raw_data, data, var_names, conf, logger):
        """extract 1d var to store them into dict"""

        logger.debug('reading 1d variables')

        for var in var_names:

            name = var[0]
            col_names = var[1]

            logger.debug('reading {}'.format(name))

            for col in col_names:
                try:
                    data[name] = raw_data[col]
                except ValueError:
                    logger.debug('column {} not found'.format(col))
                    continue

                logger.debug('column {} found'.format(col))

            # case column was not found
            if name not in data:
                data[name] = np.ones((raw_data.size,)) * conf['missing_float']

        return data


    def create_2d_var(raw_data, data, list_vars, conf, logger):
        """merge several columns of the ndarray into a 2d variable"""

        # get list of column names
        column_names = [col[0] for col in raw_data.dtype.descr]

        for var in list_vars:

            var_name = var[0]
            col_names = var[1]

            logger.debug('processing {} variables (possible pattern {})'.format(var_name, col_names))

            # find corresponding columns
            # --------------------------------------------------------------------
            col_2_join = []
            for col_name in col_names:

                # get columns which have the string in their name
                col_2_join = col_2_join + [
                    col for col in column_names if col_name in col
                ]

            # create array and fill it
            # --------------------------------------------------------------------
            var_2d = np.ones((raw_data.size, data['range'].shape[0])) * conf['missing_float']

            if len(col_2_join) != 0:
                logger.debug("corresponding columns found : {}".format(col_2_join))
                for index, col in enumerate(col_2_join):
                    var_2d[:, index] = raw_data[col]
                    logger.debug("removing column {} from processing".format(col))
                    column_names.remove(col)

                # make sure the missing values are what we want
                var_2d[np.isnan(var_2d)] = conf['missing_float']
            else:
                logger.error('no column found corresponding to {} ({})'.format(var_name, col_names))

                logger.debug('remaining available columns {}'.format(column_names))

            data[var_name] = var_2d

        return data


    def extract_time(raw_data, logger):
        """As the name of the time column could vary we search for the right one"""

        for time_var in VAR_TIME:
            try:
                data = raw_data[time_var]
                logger.debug("using {} column for time".format(time_var))
                return data
            except ValueError:
                logger.debug("column {} doesn't exists".format(time_var))
                continue

        # if we reach this point, it means we didn't
        # found the time, the reader should stop
        logger.critical("couldn't find time variable. Quitting")
        sys.exit(1)


    def read_data(list_files, conf, logger):
        """main function"""

        data = {}

        # get specific configuration
        # ------------------------------------------------------------------------
        data['time_resol'] = 600 # in seconds

        # read data from file(s)
        # ------------------------------------------------------------------------
        tmp_list = []
        for i_file, file_ in enumerate(list_files):

            if i_file == 0:
                data = read_header_data(file_, conf, data, logger)

            tmp_list.append(read_columns(file_, data, conf, logger))

        # merge data
        raw_data = merge_structured_arrays(tmp_list)

        # extract and process time var
        # ------------------------------------------------------------------------
        data['time'] = extract_time(raw_data, logger)

        # time is at end of measurements, we want it at end
        if data['time'].size == 1:
            data['start_time'] = data['time'] - dt.timedelta(seconds=data['time_resol'])
        else:
            data['start_time'] = np.array(
                [d - dt.timedelta(seconds=data['time_resol']) for d in data['time']]
            )

        # time bounds
        data['nv'] = 2
        data['time_bounds'] = np.ones((data['time'].size, data['nv']),
                                      dtype=np.dtype(dt.datetime))
        data['time_bounds'][:, 0] = data['start_time']
        data['time_bounds'][:, 1] = data['time']

        # extract 1d data
        # ------------------------------------------------------------------------
        data = create_1d_var(raw_data, data, VAR_1D, conf, logger)

        # merge data which need it into 2d array
        # ------------------------------------------------------------------------
        logger.debug('merging columns into 2d variables')
        data = create_2d_var(raw_data, data, VAR_2D, conf, logger)

        # calculate missing variables
        # ------------------------------------------------------------------------
        data['u'] = -1. * data['ws'] * np.sin(np.deg2rad(data['wd']))
        data['v'] = -1. * data['ws'] * np.cos(np.deg2rad(data['wd']))

        # W is given positive downward we prefer it upward
        # ------------------------------------------------------------------------
        data['w'] = -1. * data['w']

        return data
