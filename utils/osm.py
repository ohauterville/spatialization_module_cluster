import sys
import os
import shutil

import geopandas as gpd
import pandas as pd
import osmnx as ox
from shapely.geometry import box
from tqdm import tqdm  # Import the tqdm function from the tqdm module
from concurrent.futures import ThreadPoolExecutor
import itertools

ox.settings.requests_timeout = 15000
ox.settings.memory_only = False

CRED = "\033[31m"
CYEL = "\33[33m"
CEND = "\33[0m"

data_folder = "/data/mineralogie/hautervo/data/"
max_workers = 4
n_grid = 5


###
def create_grid(geometry, n_rows, n_cols):
    """
    Divide a large geometry into a grid of smaller bounding boxes.
    Args:
        geometry (shapely.geometry.Polygon): The large polygon to divide.
        n_rows (int): Number of rows for the grid.
        n_cols (int): Number of columns for the grid.
    Returns:
        List of smaller polygons within the grid.
    """
    minx, miny, maxx, maxy = geometry.bounds
    width = (maxx - minx) / n_cols
    height = (maxy - miny) / n_rows
    grid_polygons = []

    for i in range(n_cols):
        for j in range(n_rows):
            new_minx = minx + i * width
            new_maxx = minx + (i + 1) * width
            new_miny = miny + j * height
            new_maxy = miny + (j + 1) * height
            grid_polygons.append(box(new_minx, new_miny, new_maxx, new_maxy))
    
    return grid_polygons

def download_osm_data(
    gdf, subregion_col: str, parent_col: str, tag: str, lvl: int, country_filter: str, parallel=False
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
                print("Starting the download of ", output_file)
                osm_data = gpd.GeoDataFrame()
                polygon = row.geometry            # Get the polygon geometry of the region

                # Create a grid of smaller polygons (e.g., 5x5 grid)
                sub_polygons = create_grid(polygon, n_rows=n_grid, n_cols=n_grid)

                ### Parallel
                if parallel:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        results = list(tqdm(executor.map(fetch_osm, sub_polygons, itertools.repeat(tags)), total=n_grid**2, desc="Processing"))

                    for features in results:
                        osm_data = pd.concat([osm_data, features], ignore_index=True)
                else:
                    ### serial
                    for _polygon in tqdm(sub_polygons, desc="Processing"):
                        osm_data_small = fetch_osm(_polygon, tags)
                        osm_data = pd.concat([osm_data, osm_data_small], ignore_index=True)

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
                shutil.rmtree("/home/hautervo/cache")        
            else:
                print("File already exists: ", output_file)
        

    print("Done.")

def fetch_osm(polygon, tags):
    polygon_gs = gpd.GeoSeries([polygon], crs="EPSG:4326").loc[0]
    osm_data = ox.features_from_polygon(polygon_gs, tags)
    return osm_data

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
# oecd_iso3166_admin_units = data_folder + "/admin_units/oecd_iso3166-2/oecd_tl2_and_iso3166-2.shp"
subregion_col = "tl"+str(lvl)+"_id"
parent_col = "iso3"

country = "BEL"
parallel = False

if __name__ == "__main__":
    # shp2 = gpd.read_file(data_folder + "admin_units/iso3166-2/iso3166-2-boundaries.shp")
    # spatial_join(gpd.read_file(oecd_admin_units), shp2)
    # stop

    ### download
    print("Starting...")

    gdf = gpd.read_file(oecd_admin_units)
    gdf = gdf[gdf.is_valid & ~gdf.is_empty]

    download_osm_data(gdf, subregion_col, parent_col, "building", lvl, country_filter=country, parallel=parallel)
    # shutil.rmtree("/home/hautervo/cache")

    # merge_shp(place_list, "FR-ARA")

    print("All jobs are done.")
