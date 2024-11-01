import sys
import os
import shutil

import geopandas as gpd
import pandas as pd
import osmnx as ox

ox.settings.requests_timeout = 7200
ox.settings.memory_only = False

CRED = "\033[31m"
CYEL = "\33[33m"
CEND = "\33[0m"

# place_list = [
#     "ain",
#     "allier",
#     "ardeche",
#     "cantal",
#     "drome",
#     "isere",
#     "loire",
#     "haute-loire",
#     "puy-de-dome",
#     "rhone",
#     "savoie",
#     "haute-savoie",
# ]

# place_list = [
#     "Ariège",
#     "Aude",
#     "Aveyron",
#     "Gard",
#     "Haute-Garonne",
#     "Gers",
#     "Hérault",
#     "Lot",
#     "Lozère",
#     "Hautes-Pyrénées",
#     "Pyrénées-Orientales",
#     "Tarn",
#     "Tarn-et-Garonne",
# ]

# place_list = [
#     "Charente",
#     "Charente-Maritime",
#     "Corrèze",
#     "Creuse",
#     "Dordogne",
#     "Gironde",
#     "Landes",
#     "Lot-et-Garonne",
#     "Pyrénées-Atlantiques",
#     "Deux-Sèvres",
#     "Vienne",
#     "Haute-Vienne",
# ]

# place_list = [
#     "Ardennes",
#     "Aube",
#     "Bas-Rhin",
#     "Haut-Rhin",
#     "Haute-Marne",
#     "Marne",
#     "Meurthe-et-Moselle",
#     "Meuse",
#     "Moselle",
#     "Vosges",
# ]

# place_list = [
#     "Cote-d Or",
#     "Doubs",
#     "Jura",
#     "Nievre",
#     "Haute-Saone",
#     "Saone-et-Loire",
#     "Yonne",
#     "Belfort",
# ]

place_list = [
    # "DE-SH",
    # "DE-TH",
    # "DE-SN",
    # "DE-ST",
    # "DE-MV",
    # "DE-BB",
    "DE-NW",
    "DE-BW",
    "DE-NI",
    "DE-BY",
]

data_folder = "/data/mineralogie/hautervo/data/"


###
def download_osm_data(
    gdf, subregion_col: str, parent_col: str, tag: str, lvl: int, country_filter: str
):
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
        print("Setting by default CRS: EPSG:4326. You may want to check the original CRS to avoid errors.")
    elif gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")


    print("Downloading " + "...")

    tags = {tag: True}

    for idx, row in gdf.iterrows():
        if row[parent_col] == country_filter:
            output_path = (
                data_folder +
                "osm/"
                + tag
                + "/"
                + row[parent_col]
                + "/TL"
                + str(lvl)
                + "/"
            )
            output_file = output_path + row[subregion_col] + "/" + row[subregion_col] + ".shp"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            if not os.path.isfile(output_file):
                polygon = row.geometry            # Get the polygon geometry of the region

                polygon_gs = gpd.GeoSeries([polygon], crs="EPSG:4326").loc[0]

                osm_data = ox.features_from_polygon(polygon_gs, tags)
                # osm_data = ox.features_from_place(place, tags)

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

                ###
                # Ensure the GeoDataFrame has a CRS set
                if osm_data.crs is None:
                    osm_data = osm_data.set_crs(epsg=4326)  # Set to WGS 84 if not already set

                # Reproject to a projection that uses meters
                osm_data = osm_data.to_crs(osm_data.estimate_utm_crs())  # EPSG 3857 is a common Web Mercator projection

                osm_data.to_file(output_file)
                print("Success ", output_file)            

            else:
                print("File already exists: ", output_file)

    print("Done.")



def merge_shp(shp_list, region_nm):
    print("Starting the merge of ", region_nm)
    the_path = "/home/hautervo/Documents/Data/osm/tmp/" + region_nm + "/"

    # Initialize an empty list to store GeoDataFrames
    gdfs = []

    # Loop through each shapefile and read it into a GeoDataFrame
    for shp in shp_list:
        gdf = gpd.read_file(the_path + shp + "/" + shp + ".shp")
        gdfs.append(gdf)

    # Concatenate all GeoDataFrames into one
    merged_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

    # Ensure the CRS (Coordinate Reference System) is consistent across shapefiles
    merged_gdf.crs = gdfs[
        0
    ].crs  # Set the CRS of the merged file to match the first shapefile

    # Save the merged GeoDataFrame to a new shapefile
    merged_gdf.to_file(the_path + region_nm + ".shp")

def spatial_join(shp1 , shp2):
    # Ensure both GeoDataFrames are in the same CRS
    shp2 = shp2.to_crs(shp1.crs)

    # Perform a spatial join to combine the datasets based on their spatial overlap
    merged_gdf = gpd.sjoin(shp1, shp2, how="inner", op="intersects")
    merged_gdf.to_file(data_folder + "admin_units/oecd_iso3166-2/oecd_tl2_and_iso3166-2.shp")

# def compute_area(shp_list, with_area=False):
#     gdf = gpd.read_file(path)
#     # Ensure the GeoDataFrame has a CRS set
#     if gdf.crs is None:
#         gdf = gdf.set_crs(epsg=4326)  # Set to WGS 84 if not already set

#     # Reproject to a projection that uses meters
#     gdf = gdf.to_crs(epsg=32633)  # EPSG 3857 is a common Web Mercator projection

#     # # Compute area in square meters
#     if with_area:
#         gdf["area_m2"] = gdf["geometry"].area

#         return gdf["area_m2"].sum()
#     else:
        # return gdf["geometry"].area.sum()


### MAIN
lvl = 2

oecd_admin_units = data_folder + "OECD/admin_units/TL" + str(lvl) + "/OECD_TL" + str(lvl) + "_2020.shp"
oecd_iso3166_admin_units = data_folder + "/admin_units/oecd_iso3166-2/oecd_tl2_and_iso3166-2.shp"
subregion_col = "tl"+str(lvl)+"_id"
parent_col = "iso3"

if __name__ == "__main__":
    # shp2 = gpd.read_file(data_folder + "admin_units/iso3166-2/iso3166-2-boundaries.shp")
    # spatial_join(gpd.read_file(oecd_admin_units), shp2)
    # stop

    ### download
    print("Starting...")

    gdf = gpd.read_file(oecd_admin_units)
    gdf = gdf[gdf.is_valid & ~gdf.is_empty]

    download_osm_data(gdf, subregion_col, parent_col, "building", lvl, country_filter="FRA")
    # shutil.rmtree("/home/hautervo/cache")

    # merge_shp(place_list, "FR-ARA")

    print("All jobs are done.")
