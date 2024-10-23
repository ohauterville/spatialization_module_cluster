from Fit import Fit


class Fit_Handler:
    def __init__(self, name=""):
        self.name = name
        self.fits = []

    def add_fit(self, name: str, x, y):
        fit = Fit(name, x, y)
        self.fits.append(fit)
