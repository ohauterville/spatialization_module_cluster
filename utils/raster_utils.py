import os
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import mapping


# import matplotlib.pyplot as plt
import numpy as np
import sys

year = "2000"
type = "S"

raster_path = (
    "/home/hautervo/Documents/Data/GHSL/Built_" + type + "/E" + year + "_100m_Global/"
)
global_raster = (
    raster_path + "GHS_BUILT_S_E" + year + "_GLOBE_R2023A_54009_100_V1_0.tif"
)

output_path = raster_path + "children/"

admin_units = "/home/hautervo/Documents/Data/admin_units/world_administrative_boundaries_countries/world-administrative-boundaries.shp"


def make_children(shapefile_path, raster_path, output_path):
    shapefile = gpd.read_file(shapefile_path)
    # Ensure the shapefile geometry is in the same coordinate system as the raster
    with rasterio.open(raster_path) as src:
        crs = src.crs

    if shapefile.crs != crs:
        shapefile = shapefile.to_crs(crs)

    # Read the raster file
    with rasterio.open(raster_path) as src:
        for index, row in shapefile.iterrows():
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
            print(row.region)
            output_raster_path = os.path.join(output_path, f"{row.region}.tif")
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
                    print("Done.")


### MAIN

if __name__ == "__main__":
    # admin_units = "/home/hautervo/Documents/Data/admin_units/fra_regions_2015/regions_metropole_2015.shp"
    make_one_child(admin_units, global_raster, output_path, "iso3", "DEU")

    print("Job done.")
