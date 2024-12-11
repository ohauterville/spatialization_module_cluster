# import fiona
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import pycountry

# import matplotlib.pyplot as plt
import numpy as np
import sys

from concurrent.futures import ThreadPoolExecutor
import itertools
import os 


max_workers = 12


def create_country_mask_from_shapefile(
    Vector_gpd, src, pycountry
):
    """
    This function takes a GeoTIFF and a shapefile of administrative boundaries
    and clip the original GTIFF file along one country boundaries. To specify a country, one can
    provide its iso3 name.
    """
    code = "iso3"
    code = "GID_0"

    output_file = output_path + pycountry.alpha_3 + ".tif"
    
    if not os.path.isfile(output_file):
        try:
            Vector = Vector_gpd[Vector_gpd[code] == pycountry.alpha_3]  # Subsetting to my AOI
            
            if Vector.empty:
                print(f"No geometry found for {pycountry.alpha_3}")
                return  # Skip if there is no matching geometry for the country

            print("Start ", pycountry.alpha_3)
            with rasterio.open(global_raster) as src:
                # Vector_gpd = Vector_gpd.to_crs(src.crs)
                out_image, out_transform = mask(src, Vector.geometry, crop=True)
                out_meta = src.meta.copy()  # copy the metadata of the source DEM

                out_meta.update(
                    {
                        "driver": "Gtiff",
                        "height": out_image.shape[1],  # height starts with shape[1]
                        "width": out_image.shape[2],  # width starts with shape[2]
                        "transform": out_transform,
                        "dtype": out_image.dtype,
                        "compress": "lzw",  # lossless compression algorithm
                    }
                )

                
                os.makedirs(os.path.dirname(output_file), exist_ok="True")
                with rasterio.open(output_file, "w", **out_meta) as dest:
                    dest.write(out_image)
                    print("Success: ", output_file)
        except Exception as e:
            print(e)

    else:
        print("File already existing: ", output_file)

### MAIN
type = "V"
year = "2020"
mode = 0 # 0 for parallel, 1 for serial

###
data_folder = "/data/mineralogie/hautervo/data/"
# admin_units = data_folder + "admin_units/world_administrative_boundaries_countries/world-administrative-boundaries.shp"
admin_units = data_folder + "GADM/ESRI_54009/GADM_0_ESRI54009.shp"

# raster_path = data_folder + "GHSL/" + type + "/E" + year + "/"
# global_raster = raster_path + "GHS_" + type + "_E" + year + "_GLOBE_R2023A_54009_1000_V2_0.tif"
raster_path = data_folder + "GHSL/Built_" + type + "/E" + year + "_100m_Global/"
global_raster = raster_path + "GHS_BUILT_" + type + "_E" + year + "_GLOBE_R2023A_54009_100_V1_0.tif"

output_path = raster_path + "subregions/"

###
if __name__ == "__main__":
    print("Starting...")
    Vector_gpd = gpd.read_file(admin_units)

    with rasterio.open(global_raster) as src:
        Vector_gpd = Vector_gpd.to_crs(src.crs)

    # PARALLEL MODE
    if mode == 0:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(create_country_mask_from_shapefile, itertools.repeat(Vector_gpd), itertools.repeat(global_raster), list(pycountry.countries))
   
    # SERIAL MODE
    elif mode == 1:        
        for country in pycountry.countries:
            try:
                create_country_mask_from_shapefile(
                    Vector_gpd, global_raster, country
                )
            except Exception as err:
                print("Error for : ", country.alpha_3)
                print(f"Unexpected {err=}, {type(err)=}")

    print("Job done.")
