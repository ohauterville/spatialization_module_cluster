from GIS import GIS

import os
import sys


class GIS_Shapefile(GIS):
    def __init__(self, file, name, year, lvl):
        super().__init__(name, year, lvl)

        if os.path.exists(file):
            if file.endswith(".shp"):
                self.file = file
                self.type = "shapefile"
                self.year = year
                self.lvl = lvl
            else:
                print(
                    "The file seems to be neither a shapefile. Please check the given file."
                )
                sys.exit()
        else:
            print("The file does not exists. Check the path.")
            sys.exit()

    def make_mask(self, shapefile, region_name: str, parent_name: str, overwrite=False):
        return super().make_mask(shapefile, region_name, parent_name, overwrite=False)
