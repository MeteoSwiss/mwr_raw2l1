class MWRError(Exception):
    """Base exception for MWR"""


###############################
class MWRFileError(MWRError):
    """Base exception for MWR Files"""


class MWRInputError(MWRError):
    """Base exception for calling of MWR reader/helper function or generating measurement from it"""


class MWRDataError(MWRError):
    """Base exception if some feature of data triggers and error in a function"""


class MWROutputError(MWRError):
    """Raised when something with the output file goes wrong"""


class MWRConfigError(MWRError):
    """Raised if something with the configuration file is wrong"""


class MWRTestError(MWRError):
    """Raised if something goes wrong during set up or clean up of testing"""


################################
class UnknownFileType(MWRFileError):
    """Raised if the filetype of the datafile is not in the known range of file ID types"""


class WrongFileType(MWRFileError):
    """Raised if the filetype does not match with the chosen reader"""


class FileTooLong(MWRFileError):
    """Raised if file seems too long, e.g. if binary stream is not entirely consumed after reading is finished"""


class FileTooShort(MWRFileError):
    """Raised if file seems too short, e.g. if parameter n_meas > rest of buffer"""


class UnknownRecordType(MWRFileError):
    """Raised if Radiometrics file contains a record type number that is not known, e.g. can't be matched with header"""


class MissingVariable(MWRFileError):
    """Raised if file seems not to contain a mandatory variable. Might be due to a modified header in the input file"""


class FilenameError(MWRFileError):
    """Raised if the filename does not correspond to the expected pattern"""

# --------------------------
class WrongInputFormat(MWRInputError):
    """Raised if format of input to a function or class does not correspond to expectations"""


class UnknownFlagValue(MWRInputError):
    """Raised if the value of a flag in the input files does not correspond to the range of known values"""


class UnknownManufacturer(MWRInputError):
    """Raised if the manufacturer specified in Measurement is not known"""


class MissingTimeInput(MWRInputError):
    """Raised if time is missing in an input file but is required by the reader"""


class MissingDataSource(MWRInputError):
    """Raised if a mandatory data source for creation of Measurement is missing in input"""


class MissingInputArgument(MWRInputError):
    """Raised if a required input argument to a function or class initiation is missing"""


# --------------------------
class OutputDimensionError(MWROutputError):
    """Raised if requested output dimensions do not match data"""


# --------------------------
class MissingConfig(MWRConfigError):
    """Raised if a mandatory entry of the config file is missing"""


# --------------------------
class TimerefError(MWRError):
    """Raised if time reference is local but UTC is required"""


class WrongNumberOfChannels(MWRError):
    """Raised if a wrong number of frequency channels is assumed for reading the file
       -> this can happen for old-version BLB files where n_freq is read after being used"""


class DimensionError(MWRError):
    """Raised if specified dimensions do not match variable dimension"""

    def __init__(self, dims_required, var, n_dims_var):
        self.dims_required = dims_required
        self.var = var
        self.n_dims_var = n_dims_var

    def __str__(self):
        return "specified {} dimensions but data['{}'] is {}-dimensional".format(
            len(self.dims_required), self.var, self.n_dims_var)
