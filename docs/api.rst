API
===

The core functionality of this API happens in the following modules. *Main* guides the program flow through the *Readers*,
*Measurement* and *Write NetCDF* modules. *Readers* contain methods to load the data from the instruent's native data
files to python dictionaries. *Measurement* treats the data so that it is compatible with the desired types of output
format, e.g. transforms scans to time series, and sets quality flags (here data come as xarray datasets). *Write NetCF*
finally writes the datasets to NetCDF files according to config. The *Utils* module contains small functions to assist
the other modules.

.. toctree::
   :maxdepth: 4

   api/main
   api/readers
   api/measurement
   api/write_netcdf
   api/utils


More information on the error classes is here:

.. toctree::
   :maxdepth: 4

   api/errors

Configuration file examples are found in mwr_raw2l1.config.