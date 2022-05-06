import datetime as dt
from copy import deepcopy

import numpy as np
from pkg_resources import get_distribution

import mwr_raw2l1
from mwr_raw2l1.errors import MissingConfig, OutputDimensionError
from mwr_raw2l1.log import logger
from mwr_raw2l1.utils.config_utils import get_inst_config, get_nc_format_config

# value for _FillValue attribute of variables encoding field to have unset _FillValue in NetCDF
ENC_NO_FILLVALUE = None  # tutorials from 2017 said False must be used, but with xarray 0.20.1 only None works


class Writer(object):
    """Class for writing data (Dataset) to NetCDF according to the format definition in conf_file

    Args:
        data_in: :class:`xarray.Dataset` or :class:`DataArray` containing data to write to file. Some support is also
            provided if data_in is a dictionary, but this option is deprecated.
        filename: name and path of output NetCDF file
        conf_nc: configuration dict of yaml file defining the format and contents of the output NetCDF file
        conf_inst: configuration dict of yaml file with instrument specifications (contains global attrs for NetCDF)
        nc_format: NetCDF format type of the output file. Default is NETCDF4
        copy_data (bool): In case of False, the dataset might experience in-place modifications which is suitable when
            the dataset is not used in its original form after calling the write function, for True a copy is modified.
            Defaults to False.
    """

    def __init__(self, data_in, filename, conf_nc, conf_inst, nc_format='NETCDF4', copy_data=False):
        self.filename = filename
        self.nc_format = nc_format
        if copy_data:
            self.data = deepcopy(data_in)
        else:
            self.data = data_in

        # read in config file if config was not provided as dict
        self.conf_nc = conf_nc
        if not isinstance(self.conf_nc, dict):
            self.conf_nc = get_nc_format_config(self.conf_nc)
        self.conf_inst = conf_inst
        if not isinstance(self.conf_inst, dict):
            self.conf_inst = get_inst_config(self.conf_inst)
        self.config_dims = self.conf_nc['dimensions']['unlimited'] + self.conf_nc['dimensions']['fixed']

    def run(self):
        """write Dataset to NetCDF according to the format definition in conf_file by using the :class:`xarray` module
        """
        logger.info('Starting to write to ' + self.filename)
        self.prepare_datavars()
        self.global_attrs_from_conf(self.conf_nc, attr_key='attributes')
        self.global_attrs_from_conf(self.conf_inst, attr_key='nc_attributes')
        self.add_history_attr()
        self.add_title_attr()
        self.data.to_netcdf(self.filename, format=self.nc_format)  # write to output NetCDF file
        logger.info('Data written to ' + self.filename)

    def prepare_datavars(self):
        """prepare data variables :class:`xarray.Dataset` for writing to file standard specified in 'conf_nc'"""

        self.data.encoding.update(                                   # acts during to_netcdf()
            unlimited_dims=self.conf_nc['dimensions']['unlimited'])  # default is fixed, i.e. only need to set unlimited
        for var, specs in self.conf_nc['variables'].items():
            if var not in self.data.keys():
                if specs['optional']:
                    shape_var = tuple(map(lambda x: len(self.data[x]), specs['dim']))
                    self.data[var] = (specs['dim'], np.full(shape_var, np.nan))
                else:
                    raise KeyError('Variable {} is a mandatory input but was not found in input dictionary'.format(var))
            self.check_dims(var, specs)
            self.set_fillvalue(var, specs)
            self.data[var].encoding.update(dtype=specs['type'])
            self.data[var].attrs.update(specs['attributes'])

        self.prepare_time()
        self.append_qc_thresholds()
        self.remove_vars()
        self.rename_vars()  # must be last step

    def global_attrs_from_conf(self, conf, attr_key):
        """add global attributes from configuration dictionary

        Args:
            conf: configuration dictionary with global attributes under the key given by attr_key
            attr_key: string specifying the key under which attributes are stored in conf dict. Usually 'attributes' or
                'nc_attributes'
        """
        for attname, attval in conf[attr_key].items():
            self.data.attrs[attname] = attval

    def add_history_attr(self):
        """add global attribute 'history' with date and version of mwr_raw2l1 code run"""
        current_time_str = dt.datetime.now(tz=dt.timezone(dt.timedelta(0))).strftime('%Y%m%d')  # ensure UTC
        proj_dir = mwr_raw2l1.__file__.split('/')[-2]
        try:
            proj_dist = get_distribution(proj_dir)
            hist_str = '{}: {} ({})'.format(current_time_str, proj_dist.project_name, proj_dist.version)
        except Exception as err:  # noqa E722  # Don't want code to fail for just writing history
            hist_str = '{}: mwr_raw2l1'.format(current_time_str)
            logger.warning('Received error {} while trying to set history global attribute. Therefore, will be using '
                           'hardcoded project name without version number'.format(err))
        self.data.attrs['history'] = hist_str

    def add_title_attr(self):
        """add global attribute 'title' recombining instrument, station and operator info"""
        if 'title' in self.data.attrs:
            return  # do not overwrite a title deliberately set by config
        # specify global attributes in order they will be used to set the title
        att_seq = ['instrument_model', 'instrument_generation', 'site_location', 'institution']
        for att in att_seq:
            if att not in self.data.attrs:
                raise MissingConfig("cannot set global attribute 'title' as attribute '{}' was not found in config"
                                    .format(att))
        self.data.attrs['title'] = '{} {} MWR at {} ({})'.format(*[self.data.attrs[att] for att in att_seq])

    def check_dims(self, var, specs):
        """check dims of var (retain order of config specs, but order of coords returned by xarray Dataset is arbitrary)

        Args:
            var (str): the name of the variable of whom the dimension shall be checked
            specs: specifications for this variable from config. Must contain the key 'dim' with a list of dimensions.
        """
        if sorted(list(self.data[var].coords)) != sorted(specs['dim']):
            # if last dim of specs is missing in data and scalar, add it to data (no need for subsequent check)
            if sorted(list(self.data[var].coords)) == sorted(specs['dim'][:-1]) \
                    and specs['dim'][-1] in self.data and len(self.data[specs['dim'][-1]]) == 1:
                newdim = specs['dim'][-1]
                tmp = self.data[var].expand_dims({newdim: 1}, axis=-1)
                self.data[var] = tmp.assign_coords({newdim: self.data[newdim]})
            else:
                err_msg = "dimensions in data['{}'] (['{}']) do not match specs for output file (['{}'])".format(
                    var, "', '".join(list(self.data[var].coords)), "', '".join(specs['dim']))
                raise OutputDimensionError(err_msg)

    def set_fillvalue(self, var, specs):
        """set the fill value of var by taking care not to remove any fill value for dimensions for CF compliance

        Args:
            var (str): the name of the variable of whom the dimension shall be checked
            specs: specifications for this variable from config. Must contain the key 'dim' with a list of dimensions.
        """
        if var in self.config_dims:
            self.data[var].encoding.update(_FillValue=ENC_NO_FILLVALUE)
        else:
            self.data[var] = self.data[var].fillna(specs['_FillValue'])
            self.data[var].encoding.update(_FillValue=specs['_FillValue'])

    def prepare_time(self):
        """workaround for correctly setting units and calendar of time variable (use encoding instead of attrs)"""
        encs = {}
        for att in ['units', 'calendar']:
            encs[att] = self.data['time'].attrs.pop(att)
        self.data['time'].encoding.update(encs)

    def append_qc_thresholds(self):
        """append quality control thresholds to comment attribute of quality_flag if not refused by 'conf_nc'"""

        var = 'quality_flag'

        # cases that need no action by this method
        if var not in self.conf_nc['variables']:
            return
        if ('append_thresholds' in self.conf_nc['variables'][var] and not
                self.conf_nc['variables'][var]['append_thresholds']):
            return

        # append thresholds to comment (or set new comment if absent)
        if 'comment' in self.data[var].attrs:
            new_comment = ' '.join([self.data[var].attrs['comment'], str(self.data.qc_thresholds.values)])
        else:
            new_comment = self.data.qc_thresholds.values
        self.data[var].attrs.update({'comment': new_comment})

    def rename_vars(self):
        """set variable and dimension names to the ones set in conf_nc (CARE: must be last operation before save!)"""
        varname_map = {var: specs['name'] for var, specs in self.conf_nc['variables'].items()}
        self.data = self.data.rename(varname_map)
        # take care of encoding set for unlimited dims
        renamed_unlim_dim = [varname_map[dim] for dim in self.data.encoding['unlimited_dims']]
        self.data.encoding['unlimited_dims'] = renamed_unlim_dim

    def remove_vars(self):
        """remove undesired variables and dimensions from data (all that are not in the conf_nc)"""
        vars_to_drop = []
        for var in self.data.variables:
            if var not in self.conf_nc['variables']:
                vars_to_drop.append(var)
        self.data = self.data.drop_vars(vars_to_drop)
        dims_to_drop = []
        for var in self.data.dims:
            if var not in self.config_dims:
                dims_to_drop.append(var)
        self.data = self.data.drop_dims(dims_to_drop)
