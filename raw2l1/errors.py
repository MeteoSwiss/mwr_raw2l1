

class MWRError(Exception):
    """Base exception for MRW"""


class MWRFileError(MWRError):
    """Base exception for MRW"""


class UnknownFileType(MWRFileError):
    """Raised if the filetype of the datafile is not in the known range of file ID types"""



