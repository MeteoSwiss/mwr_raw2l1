Configuration
=============

*mwr_raw2l1* uses configuration files to customize its operation. Instrument-specific files contain receiver
characteristics and settings for processing the data. Quality control settings are specified in a distinct config file.
Finally the structure of the output file produced can be configured. There is also a file specifying the log messages
produced during operation

Examples of configuration files are found here:
https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/

* instrument config file
    :`config_0-20000-0-06610_A.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/config_0-20000-0-06610_A.yaml>`_:
        example file for settings of a RPG HATPRO instrument
    :`config_0-20000-0-06620_A.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/config_0-20000-0-06620_A.yaml>`_:
        example file for settings of a RPG TEMPRO instrument
    :`config_0-20008-0-IZO_A.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/config_0-20008-0-IZO_A.yaml>`_:
        example file for settings of a RPG LHATPRO instrument
    :`config_0-20000-0-10393_A.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/config_0-20000-0-10393_A.yaml>`_:
        example file for settings of a Radiomtetrics MP3000 instrument
    :`config_0-20000-0-99999_A.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/config_0-20000-0-99999_A.yaml>`_:
        example file for settings of an Attex MTP5-HE instrument
* output format config file
    :`L1_format.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/L1_format.yaml>`_:
        example file for setting the output file structure as used in E-PROFILE
* config file for quality checks to apply to the data (stored as flags in output file)
    :`qc_config.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/qc_config.yaml>`_:
        example for setting the quality checks and their limits as used in E-PROFILE
* configuration of the log messages issued during processing
    :`log_config.yaml <https://github.com/MeteoSwiss/mwr_raw2l1/tree/master/mwr_raw2l1/config/log_config.yaml>`_:
        example file to configure the logger

