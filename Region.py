from Df import Df
from GIS_Raster import GIS_Raster
from GIS_Shapefile import GIS_Shapefile

import os
import geopandas as gpd
import osmnx as ox
import pandas as pd

ox.settings.timeout = 600


class Region:
    def __init__(self, name: str, lvl: int, subregion_borders="", identifier="id"):
        self.name = name
        self.lvl = lvl
        self.subregion_borders = subregion_borders
        self.parent_name = None        

        self.gis_list = []
        self.df_list = []
        self.fit_list = []
        self.osm = None

        self.subregions = []
        self.c_plot = ""  # plot color

        # outputs
        self.output_df = None #supposed to be the final DF with the observed values

    def add_osm(self, name: str, tag: str):
        tags = {tag: True}

        if name.endswith(".shp"):
            gdf_boundary = gpd.read_file(name)
            if gdf_boundary.crs != "EPSG:4326":
                gdf_boundary = gdf_boundary.to_crs("EPSG:4326")
            osm_data = ox.features_from_polygon(
                gdf_boundary,
                tags,
            )
        else:
            osm_data = ox.features_from_place(name, tags)

        osm_data = osm_data[[tag, "geometry"]]

        if tag == "building" or tag == "landuse":
            osm_data = osm_data.loc[
                (osm_data.geometry.type == "Polygon")
                | (osm_data.geometry.type == "MultiPolygon")
            ]
        elif tag == "highway" or tag == "route":
            osm_data = osm_data.loc[
                (osm_data.geometry.type == "LineString")
                | (osm_data.geometry.type == "MultiLineString")
            ]
        else:
            print("Tag: ", tag, " not recognised.")

        if osm_data.crs is None:
            osm_data = osm_data.set_crs(epsg=4326)
        osm_data = osm_data.to_crs(epsg=32633)

        self.osm = osm_data

        print(self.osm.head)
        print(self.osm.shape)

    def add_df(self, file, name: str, year: str, lvl: int):
        if file.endswith(".csv"):
            self.df_list.append(Df(pd.read_csv(file), name, year, lvl))
            # print("Df ", file, " added to region ", self.name)
        else:
            print("Error: the file is not readable.")

    def add_dataframe(self, file: pd.DataFrame, name: str, year: str, lvl: int):
        self.df_list.append(Df(file, name, year, lvl))

    def add_gis(self, file, name: str, year: str, lvl: int):
        if file.endswith(".tif"):
            new_raster = GIS_Raster(file, name, year, lvl)
            self.gis_list.append(new_raster)
            # print("Raster ", file, " added to region ", self.name)
        elif file.endswith(".shp"):
            new_shp = GIS_Shapefile(file, name, year=year, lvl=lvl)
            self.gis_list.append(new_shp)
            # print("Shapefile ", file, " added to region ", self.name)
        else:
            print(file, " not added, check the file extension")

    def make_subregions(self, subregion_borders: str, subregion_col: str, parent_region_col: str, overwrite=False):
        print("START: ", self.name)
        if os.path.isfile(subregion_borders) and subregion_borders.endswith(".shp"):
            shapefile = gpd.read_file(subregion_borders)
            for index, row in shapefile.iterrows():
                if row[parent_region_col] == self.name:  # OECD specific
                    child = Region(str(row[subregion_col]), self.lvl + 1)
                    child.parent_name = self.name

                    error_check = False
                    for gis in self.gis_list:
                        if not os.path.isfile(os.path.join(os.path.dirname(gis.file), os.path.join(self.name, "subregions"),
                                    f"{row[subregion_col]}.tif",)) or overwrite:
                            sub_gis = gis.make_mask(
                                shapefile, row[subregion_col], subregion_col, self.name, overwrite=overwrite
                            )

                            if not sub_gis:
                                error_check = True
                            else:
                                child.add_gis(
                                    sub_gis,
                                    name=str(row[subregion_col]),
                                    year=gis.year,
                                    lvl=self.lvl + 1,
                                )
                        else:
                            child.add_gis(
                                    os.path.join(os.path.dirname(gis.file), os.path.join(self.name, "subregions"),
                                    f"{row[subregion_col]}.tif",),
                                    name=str(row[subregion_col]),
                                    year=gis.year,
                                    lvl=self.lvl + 1,
                                )
                        if not error_check:
                            self.subregions.append(child)
            
        else:
            print("The administrative units file does not exist or is not a shapefile.")

        print("END: ", self.name)

    def get_total_sum_pixel_values(self, band=0, pass_on=False):
        [gis.get_total_sum_pixel_values() for gis in self.gis_list]

        if pass_on and self.has_subregions():
            [
                child.get_total_sum_pixel_values(pass_on=pass_on)
                for child in self.subregions
            ]

    def has_subregions(self):
        if not self.subregions:
            return False
        else:
            return True
