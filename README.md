# mwr_raw2l1

This repository contains tools for reading brightness temperatures as well as housekeeping and auxiliary data from the
most prominent types of operational ground-based K- and V-band microwave radiometers for humidity and temperature
profiling. The read-in data can be output to NetCDF files. 
A configuration for producing a NetCDF according to the definitions for L1C01 the common E-PROFILE/ACTRIS is included in 
the repository. Additionally, each instrument needs an own config file.

The main routine does the following:
  - read in raw data files with the reader defined in the instrument's config file
  - generate an instance of the Measurement class with the read-in data
  - output the data to a NetCDF file according to the definitions in the file format config

The operational processing at the E-PROFILE hub executes the code from this repository.