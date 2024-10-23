from abc import ABC, abstractmethod
import geopandas as gpd
import numpy as np


class GIS(ABC):
    def __init__(self, name: str, year: str, lvl: int):
        self.name = name
        self.file = ""  # the main GIS
        self.type = ""  # raster of shapefile
        self.year = year
        self.level = lvl  # int, representing the hierarchy of parents

    # def get_area(self):
    #     return self.area()

    # def set_level(self, lvl: int):
    #     self.level = lvl

    # def get_level(self):
    #     return self.level

    # def add_observable(self, name, value, unit):
    #     obs = Observable(name, value, unit)
    #     self.observables.append(obs)

    @abstractmethod
    def make_mask(
        self, region_name: str, region_col_name: str, parent_name: str, overwrite=False
    ):
        pass
