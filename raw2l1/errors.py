class MWRError(Exception):
    """Base exception for MRW"""


class MWRFileError(MWRError):
    """Base exception for MRW"""


class UnknownFileType(MWRFileError):
    """Raised if the filetype of the datafile is not in the known range of file ID types"""


class WrongFileType(MWRFileError):
    """Raised if the filetype does not match with the chosen reader"""


class FileTooShort(MWRFileError):
    """Raised if file seems too short, e.g. if parameter n_meas > rest of buffer"""


class TimerefError(MWRError):
    """Raised if time reference is local but UTC is required"""
