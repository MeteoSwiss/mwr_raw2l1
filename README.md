[![CI](https://github.com/MeteoSwiss/mwr_raw2l1/actions/workflows/CI_tests.yaml/badge.svg)](https://github.com/MeteoSwiss/mwr_raw2l1/actions/workflows/CI_tests.yaml)
[![Documentation Status](https://readthedocs.org/projects/mwr-raw2l1/badge/?version=latest)](https://mwr-raw2l1.readthedocs.io/en/latest/?badge=latest)
      

# mwr_raw2l1

This repository contains tools for reading brightness temperatures as well as housekeeping and auxiliary data from the
most prominent types of operational ground-based K- and V-band microwave radiometers for humidity and temperature
profiling. The read-in data can be output to NetCDF files. 
Each instrument needs an own config file. Additionally, external config files for the output format and the quality flags
can be specified. Default configurations for producing a NetCDF according to the definitions for L1C01 the common 
[E-PROFILE](e-profile.eu)/[ACTRIS](cloudnet.fmi.fi) and defining the quality flag settings are included in the repository. 

The operational hub of E-PROFILE uses this package to generate the near real-time NetCDF messages from its network of 
ground-based microwave radiometers.

## Installation

### from *pypi*
*mwr_raw2l1* is directly installable through *pip*. To install the latest released version and its dependencies do

    pip install mwr_raw2l1

for more colorful logging you may want to do

    pip install -e colorlog mwr_raw2l1

### from *git*
To install *mwr_raw2l1* from the source code do the following
1. clone this repository

    `git clone https://github.com/MeteoSwiss/mwr_raw2l1.git`

2. go into the package directory and install
    - with *pip* (21.3)
   
        `pip install .`
   
    - with *poetry*
   
        `poetry install`
    

## Basic usage
After installing the package you get a command-line entry point called `mwr_raw2l1`.

Basic usage:

    mwr_raw2l1 CONF_INST

For more info on calling options:

    mwr_raw2l1 -h

## Advanced usage
besides using the package as a black-box with the command line interface, you might also want to choose to use parts of 
the code in python (e.g just reading in data for later usage, transform scans to time series, write E-PROFILE/ACTRIS 
compliatn NetCDF files, etc.). For these applications please refer to the [official documentation](https://mwr-raw2l1.readthedocs.io).

For a general overview, here is what the main routine does:
  - read in raw data files with the reader defined in the instrument's config file
  - generate an instance of the Measurement class. This class combines read-in data from datafile inputs with config
    file inputs, converts scans to time series if needed and applies quality checks to set the qualtiy flag.
  - output the data to a NetCDF file according to the definitions in the file format config


## Documentation
The official documentation is available [here](https://mwr-raw2l1.readthedocs.io)

## Licnese
[BSD 3-Clause](LICENSE)
