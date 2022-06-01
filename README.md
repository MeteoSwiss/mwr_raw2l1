[![CI](https://github.com/MeteoSwiss/mwr_raw2l1/actions/workflows/CI_tests.yaml/badge.svg)](https://github.com/MeteoSwiss/mwr_raw2l1/actions/workflows/CI_tests.yaml)
[![Documentation Status](https://readthedocs.org/projects/mwr-raw2l1/badge/?version=latest)](https://mwr-raw2l1.readthedocs.io/en/latest/?badge=latest)
      

# mwr_raw2l1

This repository contains tools for reading brightness temperatures as well as housekeeping and auxiliary data from the
most prominent types of operational ground-based K- and V-band microwave radiometers for humidity and temperature
profiling. The read-in data can be output to NetCDF files. 
Each instrument needs an own config file. Additionally, external config files for the output format and the quality flags
can be specified. Default configurations for producing a NetCDF according to the definitions for L1C01 the common 
E-PROFILE/ACTRIS and defining the quality flag settings are included in the repository. 

After installing the package you get an entry point called `mwr_raw2l1`\
Basic usage:
`mwr_raw2l1 CONF_INST`\
For more info on calling options:
`mwr_raw2l1 -h`


The main routine does the following:
  - read in raw data files with the reader defined in the instrument's config file
  - generate an instance of the Measurement class. This class combines read-in data from datafile inputs with config
    file inputs and applies quality checks.
  - output the data to a NetCDF file according to the definitions in the file format config

The operational processing at the E-PROFILE hub executes the code from this repository.