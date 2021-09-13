

class MWRError(Exception):
    """Base exception for MRW"""


class MWRFileError(MWRError):
    """Base exception for MRW"""


class UnknownFileType(MWRFileError):
    """Raised if the filetype of the bla bla bla is not in the known range of file ID types"""

class FileToShort(MWRFileError):
    """Raised if the filetype of the bla bla bla is not in the known range of file ID types"""

