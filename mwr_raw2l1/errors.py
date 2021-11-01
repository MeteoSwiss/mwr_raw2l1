class MWRError(Exception):
    """Base exception for MWR"""


###############################
class MWRFileError(MWRError):
    """Base exception for MWR Files"""


class MWRInputError(MWRError):
    """Base exception for calling of MWR reader/helper function"""


################################
class UnknownFileType(MWRFileError):
    """Raised if the filetype of the datafile is not in the known range of file ID types"""


class WrongFileType(MWRFileError):
    """Raised if the filetype does not match with the chosen reader"""


class FileTooShort(MWRFileError):
    """Raised if file seems too short, e.g. if parameter n_meas > rest of buffer"""


# --------------------------
class WrongInputFormat(MWRInputError):
    """Raised if format of input to a function or class does not correspond to expectations"""


# --------------------------
class TimerefError(MWRError):
    """Raised if time reference is local but UTC is required"""


class WrongNumberOfChannels(MWRError):
    """Raised if a wrong number of frequency channels is assumed for reading the file
       -> this can happen for old-version BLB files where n_freq is read after being used"""


