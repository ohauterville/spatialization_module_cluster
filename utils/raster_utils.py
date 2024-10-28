import os
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import mapping
from concurrent.futures import ThreadPoolExecutor
import itertools

# import matplotlib.pyplot as plt
import numpy as np
import sys


max_workers = 32


def make_children(shapefile_path, raster_path, output_path, col_name: str):
    shapefile = gpd.read_file(shapefile_path)
     
    with rasterio.open(raster_path) as src:  
        crs = src.crs

    if shapefile.crs != crs:
        shapefile = shapefile.to_crs(crs)
    # Read the raster file
    with rasterio.open(raster_path) as src:      

        for index, row in shapefile.iterrows():
            # print(row)
            geometry = row.geometry
            shape = [mapping(geometry)]

            # Mask the raster with the individual shape
            out_image, out_transform = mask(src, shape, crop=True)
            out_meta = src.meta.copy()

            # Update the metadata with new dimensions, transform, and CRS
            out_meta.update(
                {
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "dtype": out_image.dtype,
                    "compress": "lzw",  # lossless compression algorithm
                }
            )

            # Define the output raster path
            output_raster_path = os.path.join(output_path, f"{row[col_name]}.tif")
            os.makedirs(os.path.dirname(output_raster_path), exist_ok=True)

            # Save the clipped raster to a new file
            with rasterio.open(output_raster_path, "w", **out_meta) as dest:
                dest.write(out_image)


def make_one_child(shapefile_path, raster_path, output_path, col_name: str, id: str):
    shapefile = gpd.read_file(shapefile_path)
    # Ensure the shapefile geometry is in the same coordinate system as the raster
    with rasterio.open(raster_path) as src:
        crs = src.crs

    if shapefile.crs != crs:
        shapefile = shapefile.to_crs(crs)

    # Read the raster file
    with rasterio.open(raster_path) as src:
        for index, row in shapefile.iterrows():
            if id == row[col_name]:
                print("Found: ", row[col_name])
                geometry = row.geometry
                shape = [mapping(geometry)]

                # Mask the raster with the individual shape
                out_image, out_transform = mask(src, shape, crop=True)
                out_meta = src.meta.copy()

                # Update the metadata with new dimensions, transform, and CRS
                out_meta.update(
                    {
                        "driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform,
                        "dtype": out_image.dtype,
                        "compress": "lzw",  # lossless compression algorithm
                    }
                )

                # Define the output raster path
                output_raster_path = os.path.join(output_path, f"{row[col_name]}.tif")
                os.makedirs(os.path.dirname(output_raster_path), exist_ok=True)

                # Save the clipped raster to a new file
                with rasterio.open(output_raster_path, "w", **out_meta) as dest:
                    dest.write(out_image)
                print("END ", output_raster_path)


### MAIN
type = "POP"

data_folder = "/data/mineralogie/hautervo/data/"
admin_units = data_folder + "admin_units/world_administrative_boundaries_countries/world-administrative-boundaries.shp"

years = ["1990", "2010"]
loop_raster = []
loop_output_path = []

for year in years:
    raster_path = data_folder + "GHSL/Built_" + type + "/E" + year + "_100m_Global/"
    loop_raster.append(raster_path + "GHS_BUILT_" + type + "_E" + year + "_GLOBE_R2023A_54009_100_V1_0.tif")
    loop_output_path.append(raster_path + "subregions/")


if __name__ == "__main__":
    # with ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     executor.map(make_one_child, itertools.repeat(admin_units), itertools.repeat(global_raster), itertools.repeat(output_path), itertools.repeat("iso3"), )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(make_children, itertools.repeat(admin_units), loop_raster, loop_output_path, itertools.repeat("iso3"), )

    print("Job done.")
