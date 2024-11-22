from Df import Df
from GIS_Raster import GIS_Raster
from GIS_Shapefile import GIS_Shapefile

import os
import geopandas as gpd
import osmnx as ox
import pandas as pd

from functools import reduce
from termcolor import colored

ox.settings.timeout = 6000


class Region:
    def __init__(self, name: str, lvl: int,):
        self.name = name
        self.lvl = lvl
        self.parent_name = None  

        self.geometry = None
        self.crs = None
      

        self.gis_list = []
        self.df_list = []
        self.fit_list = []
        self.osm_list = []

        self.output_df_list = []
        self.output_df_merged = None

        self.subregions = []
        self.c_plot = ""  # plot color

        # outputs
        self.output_df = None #supposed to be the final DF with the observed values

    def get_osm_by_tag(self, place_name: str, tag: str, place_geometry=None, crs="EPSG:4326"):
        """
        If place_geometry is given, the function will take the osm tags within this area
        """
        tags = {tag: True}

        if place_geometry:
            if crs != "EPSG:4326":
                gdf = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[place_geometry])  # Assuming the original CRS is WGS84 (EPSG:4326)
                gdf = gdf.to_crs("EPSG:4326")
                place_geometry = gdf.geometry.iloc[0]

            osm_data = ox.features_from_polygon(place_geometry, tags,)
        else: 
            osm_data = ox.features_from_place(place_name, tags)

        ###   
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

        ### save
        self.osm_list.append(Df(osm_data), place_name) 

        print(self.osm_list[-1].df.head)
        print(self.osm_list[-1].df.shape)

    def add_df(self, file, name: str):
        if file.endswith(".csv"):
            self.df_list.append(Df(pd.read_csv(file), name))
            # print("Df ", file, " added to region ", self.name)
        else:
            print("Error: the file is not readable.")

    def add_dataframe(self, file: pd.DataFrame, name: str):
        self.df_list.append(Df(file, name))

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

    def merge_output_dfs(self, col:str):
        df_list = []
        for df in self.output_df_list:
            df_list.append(df.df)
            
        self.output_df_merged = reduce(lambda left, right: pd.merge(left, right, on=col), df_list)


    def make_subregions(self, gpd_admin_units, subregion_col: str, parent_region_col: str, overwrite=False):
        for index, row in gpd_admin_units.iterrows():
            if row[parent_region_col] == self.name:  # OECD specific
                subregion = Region(str(row[subregion_col]), self.lvl + 1)
                subregion.parent_name = self.name
                subregion.geometry = row.geometry
                subregion.crs = gpd_admin_units.crs

                for gis in self.gis_list:
                    if not os.path.isfile(os.path.join(os.path.dirname(gis.file), os.path.join(self.name, "subregions"),
                                f"{row[subregion_col]}.tif",)) or overwrite:
                        sub_gis = gis.make_mask(
                            gpd_admin_units, row[subregion_col], subregion_col, self.name, overwrite=overwrite
                        )

                        if not sub_gis:
                            print("Something went wrong with the mask!")
                        else:
                            subregion.add_gis(
                                sub_gis,
                                name=gis.name,
                                year=gis.year,
                                lvl=self.lvl + 1,
                            )
                    else:
                        subregion.add_gis(
                                os.path.join(os.path.dirname(gis.file), os.path.join(self.name, "subregions"),
                                f"{row[subregion_col]}.tif",),
                                name=gis.name,
                                year=gis.year,
                                lvl=self.lvl + 1,
                            )
                        
                ###
                self.subregions.append(subregion)

        print(colored("END: {self.name}", "green"))

    def make_subregions_visual(self, gpd_admin_units, subregion_col: str, parent_region_col: str, output_csv_paths: list, years):
        # this function is meant to be use for the visualization part only, not the preprocessing one.
        # TODO: output_csv_path and output_name should be a list to loop on
        for index, row in gpd_admin_units.iterrows():
            if row[parent_region_col] == self.name:  # OECD specific
                try:
                    subregion = Region(str(row[subregion_col]), self.lvl + 1)
                    subregion.parent_name = self.name
                    for output_csv_path in output_csv_paths:
                        subregion.output_df_list.append(Df(pd.read_csv(os.path.join(output_csv_path, subregion.parent_name, subregion.name, '_'.join(years))+".csv"), ""))
                    subregion.merge_output_dfs("year")
                    self.subregions.append(subregion)
                except Exception as e:
                    print(e)
    
    def compute_own_df(self, years, type: str):
        # TODO: this should be changed to use the output_df_list instead
        if type == "GHSL_OECD":
            self.output_df = pd.DataFrame({"year": years, "GDP per capita":None, "Population_OECD": None, "Population_GHSL":None, "Built up surface GHSL/Population_OECD": None, "Population_OECD/Total surface": None})

            for y in years:
                gdp_sum = 0
                population_OECD = 0
                population_GHSL = 0
                ghsl_surface = 0
                total_surface = 0

                for subregion in self.subregions:                  
                    # intensive
                    population_GHSL += subregion.output_df.loc[subregion.output_df["year"]==int(y), "Population_GHSL"].sum()
                    population_OECD += subregion.output_df.loc[subregion.output_df["year"]==int(y), "Population_OECD"].sum()
                    ghsl_surface += subregion.output_df.loc[subregion.output_df["year"]==int(y), "Built up surface GHSL"].sum()
                    total_surface += subregion.output_df.loc[subregion.output_df["year"]==int(y), "Total surface"].sum()
                    # extensive
                    gdp_sum += subregion.output_df.loc[subregion.output_df["year"]==int(y), "GDP per capita"].sum() * subregion.output_df.loc[subregion.output_df["year"]==int(y), "Population_OECD"].sum()
                
                # Finally
                if population_OECD != 0:
                    if gdp_sum != 0:
                        self.output_df.loc[self.output_df["year"]==y, "GDP per capita"] = gdp_sum/population_OECD
                    else:
                        pass

                    self.output_df.loc[self.output_df["year"]==y, "Built up surface GHSL/Population_OECD"] = ghsl_surface / population_OECD
                    self.output_df.loc[self.output_df["year"]==y, "Population_OECD"] = population_OECD
                    self.output_df.loc[self.output_df["year"]==y, "Population_OECD/Total surface"] = population_OECD / total_surface
                
                # same but with the pop computed by GHSL
                if gdp_sum != 0:
                    self.output_df.loc[self.output_df["year"]==y, "GDP per capita"] = gdp_sum/population_GHSL
                else:
                    pass
        
                self.output_df.loc[self.output_df["year"]==y, "Built up surface GHSL/Population_GHSL"] = ghsl_surface / population_GHSL
                self.output_df.loc[self.output_df["year"]==y, "Population_GHSL"] = population_GHSL
                self.output_df.loc[self.output_df["year"]==y, "Population_GHSL/Total surface"] = population_GHSL / total_surface

                # these should always be found
                self.output_df.loc[self.output_df["year"]==y, "Built up surface GHSL"] = ghsl_surface
                self.output_df.loc[self.output_df["year"]==y, "Total surface"] = total_surface

    def compute_vector_area(self, gis_name: str, output_df_name: str):
        vector = next((x for x in self.gis_list if x.name == gis_name), None)
        if vector is not None:
            value = (vector['geometry'].area).sum()
            df = pd.DataFrame({"area": value})
            self.output_df_list.append(Df(df, output_df_name))
        else: 
            print(f"The gis: {gis_name} was not found.")


    def delete_lists(self, pass_on=False):
        try:
            del self.subregion_borders
        except:
            pass
        
        for gis in self.gis_list:
            del gis
        
        for df in self.df_list:
            del df

        if pass_on and self.has_subregions():
            [
                subregion.delete_lists(pass_on=pass_on)
                for subregion in self.subregions
            ]            
  

    # def get_total_sum_pixel_values(self, band=0, pass_on=False):
    #     [gis.get_total_sum_pixel_values() for gis in self.gis_list]

    #     if pass_on and self.has_subregions():
    #         [
    #             subregion.get_total_sum_pixel_values(pass_on=pass_on)
    #             for subregion in self.subregions
    #         ]

    def has_subregions(self):
        if not self.subregions:
            return False
        else:
            return True
