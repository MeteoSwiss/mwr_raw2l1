class BaseMeasurement:
    def __init__(self):
        self.data = None

    @classmethod
    def from_signal(cls, signal_a, signal_b):
        result = cls()
        result.combine(signal_a, signal_b)
        return result

    def combine(self, signal_a, signal_b):
        self.data = signal_b + signal_a
        pass

    # TODO: use 3 different class methods to read in data from the different instruments to a common measurement class
    # don't need a BaseMeasurement class in this case as only 1. Measurement class can then be handed over to writer

    # TODO: for combining RPG files to time series use xarray dataset. For writing, minght maybe still use netCDF4