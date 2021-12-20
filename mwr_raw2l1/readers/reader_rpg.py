"""
readers for the different binary files from RPG radiometers (HATPRO, TEMPRO or HUMPRO)
"""
import glob
import os

import numpy as np

from mwr_raw2l1.errors import WrongFileType, WrongNumberOfChannels
from mwr_raw2l1.log import logger
from mwr_raw2l1.readers.base_reader_rpg import BaseReader
from mwr_raw2l1.readers.reader_rpg_helpers import (interpret_hkd_contents_code,
                                                   interpret_met_auxsens_code,
                                                   interpret_scanflag,
                                                   interpret_statusflag)

N_FREQ_DEFAULT = 14    # needed before as freq used before read-in in old BRT file format
# TODO: check how RPG deals with files from TEMPRO or HUMPRO how would have different n_freq. Other filecodes?


class BRT(BaseReader):
    def interpret_filecode(self):
        super(BRT, self).interpret_filecode()

        # check if filecode corresponds to a BRT file
        if self.filestruct['type'] != 'brt':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for BRT'.format(
                                self.filestruct['type']))

    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_meas', type='i', shape=(1,)),
            dict(name='timeref', type='i', shape=(1,)),
            dict(name='n_freq', type='i', shape=(1,))]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        n_freq = self.data['n_freq']
        encodings_bin_var = [
            dict(name='frequency', type='f', shape=(n_freq,)),
            dict(name='Tb_min', type='f', shape=(n_freq,)),
            dict(name='Tb_max', type='f', shape=(n_freq,))]
        self.decode_binary(encodings_bin_var)

    def _read_meas(self):
        """read actual measurements. Filecode and Header needs to be read before as info is needed for decoding"""
        n_freq = self.data['n_freq']
        encodings_bin = (
            dict(name='time_raw', type='i', shape=(1,)),
            dict(name='rainflag', type='B', shape=(1,)),
            dict(name='Tb', type='f', shape=(n_freq,)),
            dict(name='pointing_raw', type=self.filestruct['formatchar_angle'], shape=(1,)))
        self.decode_binary_np(encodings_bin, self.data['n_meas'])


class BLB(BaseReader):
    def __init__(self, filename, accept_localtime=False):
        self.header_reader = None
        super(BLB, self).__init__(filename, accept_localtime)

    def interpret_filecode(self):
        super(BLB, self).interpret_filecode()

        # check if filecode corresponds to a BLB file
        if self.filestruct['type'] != 'blb':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for BLB'.format(
                                self.filestruct['type']))

        self.header_reader = getattr(self, '_read_header_{:d}'.format(self.filestruct['structver']))

    def _read_header(self):
        self.header_reader()

    def _read_header_1(self):
        """Function for reading header for files with structver 1 (n_freq first assumed and read only afterwards)"""
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_scans', type='i', shape=(1,))]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        self.data['n_freq'] = N_FREQ_DEFAULT  # need assumption as number of channels is encoded after used for read
        n_freq = self.data['n_freq']
        encodings_bin_var_1 = [
            dict(name='Tb_min', type='f', shape=(n_freq,)),
            dict(name='Tb_max', type='f', shape=(n_freq,)),
            dict(name='timeref', type='i', shape=(1,)),
            dict(name='n_freq_file', type='i', shape=(1,)),
            dict(name='frequency', type='f', shape=(n_freq,)),
            dict(name='n_ele', type='i', shape=(1,))]
        self.decode_binary(encodings_bin_var_1)

        # quantities with length dependent on number of elevations in scan (n_ele) only possible after n_ele is read
        n_ele = self.data['n_ele']
        encodings_bin_var_2 = [
            dict(name='scan_ele', type='f', shape=(n_ele,))]
        self.decode_binary(encodings_bin_var_2)

    def _read_header_2(self):
        """Function for reading header for files with structver 2 (no assumption on n_freq needed"""
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_scans', type='i', shape=(1,)),
            dict(name='n_freq', type='i', shape=(1,))]
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_freq) only possible after n_freq is read
        n_freq = self.data['n_freq']
        encodings_bin_var_1 = [
            dict(name='Tb_min', type='f', shape=(n_freq,)),
            dict(name='Tb_max', type='f', shape=(n_freq,)),
            dict(name='timeref', type='i', shape=(1,)),
            dict(name='frequency', type='f', shape=(n_freq,)),
            dict(name='n_ele', type='i', shape=(1,))]
        self.decode_binary(encodings_bin_var_1)

        # quantities with length dependent on number of elevations in scan (n_ele) only possible after n_ele is read
        n_ele = self.data['n_ele']
        encodings_bin_var_2 = [
            dict(name='scan_ele', type='f', shape=(n_ele,))]
        self.decode_binary(encodings_bin_var_2)

    def interpret_header(self):
        super(BLB, self).interpret_header()
        self.data['n_meas'] = self.data['n_scans'] * self.data['n_ele']

        # check if correct number of channels was assumed for reading in structver 1 file
        if 'n_freq_file' in self.data.keys():
            if self.data['n_freq_file'] != self.data['n_freq']:
                raise WrongNumberOfChannels(
                    'assumed number of channels ({}) for reading this BLB file seems wrong'.format(self.data['n_freq']))

    def _read_meas(self):
        n_ele = self.data['n_ele']
        n_freq = self.data['n_freq']
        encodings_bin = (
            dict(name='time_raw', type='i', shape=(1,)),  # scan starttime here, will be transformed to series
            dict(name='scanflag', type='B', shape=(1,)),
            dict(name='scanobs', type='f', shape=(n_freq, n_ele+1)))  # Tb on n_ele + T (stored at n_ele+1)
        self.decode_binary_np(encodings_bin, self.data['n_scans'])

    def interpret_raw_data(self):
        super(BLB, self).interpret_raw_data()
        self.interpret_scanobs()
        self.data.update(interpret_scanflag(self.data['scanflag']))

    def interpret_scanobs(self):
        """transform scanobs 3D array to time series of spectra and temperature"""

        # extract ambient temperature (ambient temperature equal for each frequency, one per scan)
        self.data['T_per_scan'] = self.data['scanobs'][:, 0, -1]

        # extract spectra of brightness temperatures for each ele in dimension (time, freq, ele)
        self.data['Tb_scan'] = self.data['scanobs'][:, :, :-1]


class IRT(BaseReader):
    def interpret_filecode(self):
        super(IRT, self).interpret_filecode()

        # check if filecode corresponds to a IRT file
        if self.filestruct['type'] != 'irt':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for IRT'.format(
                                self.filestruct['type']))

    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = [
            dict(name='n_meas', type='i', shape=(1,)),
            dict(name='IRT_min', type='f', shape=(1,)),
            dict(name='IRT_max', type='f', shape=(1,)),
            dict(name='timeref', type='i', shape=(1,))]  # define as list to be able to append.
        if self.filestruct['structver'] >= 2:
            encodings_bin_fix.append(
                dict(name='n_wavelengths', type='i', shape=(1,)))
        self.decode_binary(encodings_bin_fix)

        # quantities with length dependent on number of spectral channels (n_wavelenghts) only possible after read
        n_wl = self.data['n_wavelengths']
        encodings_bin_var = [
            dict(name='wavelength', type='f', shape=(n_wl,))]
        self.decode_binary(encodings_bin_var)

        # complete missing input for structver == 1
        if self.filestruct['structver'] == 1:
            self.data['n_wavelengths'] = 1
            self.data['wavelength'] = np.nan

    def _read_meas(self):
        n_wl = self.data['n_wavelengths']
        encodings_bin = [
            dict(name='time_raw', type='i', shape=(1,)),
            dict(name='rainflag', type='B', shape=(1,)),
            dict(name='IRT', type='f', shape=(n_wl,))]
        if self.filestruct['structver'] >= 2:
            encodings_bin.append(
                dict(name='pointing_raw', type=self.filestruct['formatchar_angle'], shape=(1,)))

        self.decode_binary_np(encodings_bin, self.data['n_meas'])


class MET(BaseReader):
    def interpret_filecode(self):
        super(MET, self).interpret_filecode()

        # check if filecode corresponds to a MET file
        if self.filestruct['type'] != 'met':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for MET'.format(
                                self.filestruct['type']))

    def _read_header(self):
        # quantities with fixed length
        encodings_bin_fix = [dict(name='n_meas', type='i', shape=(1,))]
        if self.filestruct['structver'] >= 2:
            encodings_bin_fix.append(dict(name='auxsens_code', type='B', shape=(1,)))
        for var in ['p_min', 'p_max', 'T_min', 'T_max', 'RH_min', 'RH_max']:
            encodings_bin_fix.append(dict(name=var, type='f', shape=(1,)))  # the variables all have same type and shape
        self.decode_binary(encodings_bin_fix)

        # interpret availability of auxiliary sensor data
        auxsens_input = None if 'auxsens_code' not in self.data else self.data['auxsens_code']
        auxsens_contents = interpret_met_auxsens_code(auxsens_input)
        self.data.update(auxsens_contents)

        # quantities with existence depending on auxsens contents
        encodings_bin_var = []
        if self.data['has_windspeed']:
            encodings_bin_var.append(dict(name='windspeed_min', type='f', shape=(1,)))
            encodings_bin_var.append(dict(name='windspeed_max', type='f', shape=(1,)))
        if self.data['has_winddir']:
            encodings_bin_var.append(dict(name='winddir_min', type='f', shape=(1,)))
            encodings_bin_var.append(dict(name='winddir_max', type='f', shape=(1,)))
        if self.data['has_rainrate']:
            encodings_bin_var.append(dict(name='rainrate_min', type='f', shape=(1,)))
            encodings_bin_var.append(dict(name='rainrate_max', type='f', shape=(1,)))
        encodings_bin_var.append(dict(name='timeref', type='i', shape=(1,)))
        self.decode_binary(encodings_bin_var)

    def _read_meas(self):
        encodings_bin = [dict(name='time_raw', type='i', shape=(1,)),
                         dict(name='rainflag', type='B', shape=(1,)),
                         dict(name='p', type='f', shape=(1,)),
                         dict(name='T', type='f', shape=(1,)),
                         dict(name='RH', type='f', shape=(1,))]
        if self.data['has_windspeed']:
            encodings_bin.append(dict(name='windspeed', type='f', shape=(1,)))
        if self.data['has_winddir']:
            encodings_bin.append(dict(name='winddir', type='f', shape=(1,)))
        if self.data['has_rainrate']:
            encodings_bin.append(dict(name='rainrate', type='f', shape=(1,)))

        self.decode_binary_np(encodings_bin, self.data['n_meas'])


class HKD(BaseReader):
    def interpret_filecode(self):
        super(HKD, self).interpret_filecode()

        # check if filecode corresponds to a HKD file
        if self.filestruct['type'] != 'hkd':
            raise WrongFileType('filecode of input file corresponds to a {}-file but this reader is for HKD'.format(
                                self.filestruct['type']))

    def _read_header(self):
        encodings_bin = [
            dict(name='n_meas', type='i', shape=(1,)),
            dict(name='timeref', type='i', shape=(1,)),
            dict(name='hkd_contents_code', type='i', shape=(1,))]
        self.decode_binary(encodings_bin)

        file_contents = interpret_hkd_contents_code(self.data['hkd_contents_code'])
        self.data.update(file_contents)  # add variables 'has_...' used below to the data dictionary

    def _read_meas(self):
        encodings_bin = [
            dict(name='time_raw', type='i', shape=(1,)),
            dict(name='alarm', type='B', shape=(1,))]
        if self.data['has_coord']:
            encodings_bin.append(dict(name='lon_raw', type='f', shape=(1,)))
            encodings_bin.append(dict(name='lat_raw', type='f', shape=(1,)))
        if self.data['has_T']:
            encodings_bin.append(dict(name='T_amb_1', type='f', shape=(1,)))
            encodings_bin.append(dict(name='T_amb_2', type='f', shape=(1,)))
            encodings_bin.append(dict(name='T_receiver_kband', type='f', shape=(1,)))
            encodings_bin.append(dict(name='T_receiver_vband', type='f', shape=(1,)))
        if self.data['has_stability']:
            encodings_bin.append(dict(name='Tstab_kband', type='f', shape=(1,)))
            encodings_bin.append(dict(name='Tstab_vband', type='f', shape=(1,)))
        if self.data['has_flashmemoryinfo']:
            encodings_bin.append(dict(name='flashmemory_remaining', type='i', shape=(1,)))
        if self.data['has_qualityflag']:
            encodings_bin.append(dict(name='L2_qualityflag', type='i', shape=(1,)))
        if self.data['has_statusflag']:
            encodings_bin.append(dict(name='statusflag', type='i', shape=(1,)))

        self.decode_binary_np(encodings_bin, self.data['n_meas'])

    def interpret_raw_data(self):
        super(HKD, self).interpret_raw_data()
        self.data.update(interpret_statusflag(self.data['statusflag']))


# TODO: Consider transforming to SI units. IRT/IRT_min/IRT_max -> K; wavelength -> m; frequency -> Hz. could be done in interpret_raw_data of BaseReader class


def read_all(dir_in, basename, time_start=None, time_end=None):
    """read all L1-related files in dir_in corresponding to basename

    Args:
        dir_in: directory where files of the respective instrument are located
        basename: full identifier including station and inst id
        time_start/time_end: To be implemented: Filter to just read files between these times
    Returns:
        dictionary with keys brt, blb, irt, met, hkd containing list with all read-in class instances for the
        corresponding file extension matching basename and the timing requirement.
        """

    # assign reader (value) to lowercase file extension (key). All keys will have an entry in the output dictionary
    reader_for_ext = {'brt': BRT, 'blb': BLB, 'irt': IRT, 'met': MET, 'hkd': HKD}

    files_all_times = glob.glob(os.path.join(dir_in, basename + '*'))

    files = files_all_times  # TODO choose files according to time_start and time_end instead of using all

    all_data = {name: [] for name in reader_for_ext}  # use file extension as name for list of instances of reader type
    for file in files:
        ext = os.path.splitext(file)[1].lower()[1:]  # omit dot from extension
        if ext in reader_for_ext:
            data_act = reader_for_ext[ext](file)
            all_data[ext].append(data_act)
            # TODO: decide what to do with processed files. Leave where they are, delete or move to other folder
        else:
            # TODO: decide what to do with unprocessable files. Leave where they are, delete or move to other folder
            logger.warn('Cannot read {} as no reader is specified for files with extension "{}"'.format(file, ext))

    return all_data


def main():

    base_filename = 'C00-V859_190803'

    filename_noext = os.path.splitext('data/rpg/' + base_filename)[0]  # join path and make sure that filename has no extension

    brt = BRT(filename_noext + '.BRT')
    blb = BLB(filename_noext + '.BLB')
    irt = IRT(filename_noext + '.IRT')
    met = MET(filename_noext + '.MET')
    hkd = HKD(filename_noext + '.HKD')

    # # generate new pickle of the read-in data
    # dir_pickle = 'tests/data/rpg/'
    # vars = [brt, blb, irt, met, hkd]
    # varnames = ['brt', 'blb', 'irt', 'met', 'hkd']
    # for var, varname in zip(vars, varnames):
    #     outfile = dir_pickle + '/' + base_filename + '_' + varname + '.pkl'
    #     pickle_dump(var.data, outfile)  # only store data dict in pickle

    # # legacy readers
    # brt_old = read_brt(filename_noext + '.BRT')
    # blb_old = read_blb(filename_noext + '.BLB')
    # irt_old = read_irt(filename_noext + '.IRT')
    # met_old = read_met(filename_noext + '.MET')
    # hkd_old = read_hkd(filename_noext + '.HKD')

    del(brt, blb, irt, met, hkd)  # to avoid warning for unused variables by pylint


if __name__ == '__main__':
    # main()
    all_data = read_all('../data/rpg/', 'C00-V859')
    pass
