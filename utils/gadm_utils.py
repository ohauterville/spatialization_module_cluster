# import fiona
import rasterio
from rasterio.mask import mask
import geopandas as gpd

from concurrent.futures import ThreadPoolExecutor
import itertools
import os 
import sys

max_workers = 12

def create_country_mask_from_shapefile(
    region, code: str, global_raster
):
    """
    This function takes a GeoTIFF and a shapefile of administrative boundaries
    and clip the original GTIFF file along one country boundaries. To specify a country, one can
    provide its iso3 name.
    """
    output_file = output_path + getattr(region, code) + ".tif"  # Access attribute with getattr    
    
    if not os.path.isfile(output_file):
        try:
            print("Start ", getattr(region, code))
            with rasterio.open(global_raster) as src:
                out_image, out_transform = mask(src, [region.geometry], crop=True)
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

from rasterio.merge import merge
import glob

def merge_raster(folder:str, output_file:str):
    # Define a list of paths to the subnational TIFF files
    tiff_files = glob.glob(folder+"*.tif")

    # Open the TIFF files as datasets
    datasets = [rasterio.open(tiff) for tiff in tiff_files]

    # Merge the datasets
    merged_data, merged_transform = merge(datasets)

    # Get metadata from the first file to use in the output
    out_meta = datasets[0].meta.copy()

    # Update metadata to match the merged raster
    out_meta.update({
        "driver": "GTiff",
        "height": merged_data.shape[1],
        "width": merged_data.shape[2],
        "transform": merged_transform,
        "dtype": merged_data.dtype,
        "compress": "lzw",  # lossless compression algorithm
    })

    # Write the merged raster to a new file
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(merged_data)

    # Close the datasets
    for dataset in datasets:
        dataset.close()

    print("Merged TIFF f'")


### MAIN
# import logging
# logging.basicConfig(level=logging.DEBUG)

type = "POP"
year = "1975"
mode = 1 # 0 for parallel, 1 for serial

###
data_folder = "/data/mineralogie/hautervo/data/"
# admin_units = data_folder + "admin_units/world_administrative_boundaries_countries/world-administrative-boundaries.shp"
admin_units = data_folder + "GADM/ESRI_54009/GADM_1_ESRI54009.shp"
# admin_units = data_folder + "OECD/admin_units/Country/OECD_Country_2020_simple1.shp"
code = "GID_1"
# code = "iso3"

raster_path = data_folder + "GHSL/Built_" + type + "/E" + year + "_100m_Global/"
global_raster = raster_path + "GHS_BUILT_" + type + "_E" + year + "_GLOBE_R2023A_54009_100_V1_0.tif"

output_path = raster_path + "subregions/USA/"

###
if __name__ == "__main__":
    print("Starting...")
    # merge_raster(output_path+"USA/", output_path+"USA.tif")
    # sys.exit()
    ###
    regions_gpd = gpd.read_file(admin_units)

    # regions_gpd = regions_gpd[regions_gpd["GID_0"] != "ATA"] # ignore antartica
    regions_gpd = regions_gpd[regions_gpd["GID_0"] == "USA"]
    regions_gpd = regions_gpd[~regions_gpd.geometry.isnull()]

    with rasterio.open(global_raster) as src:
        if regions_gpd.crs != src.crs:
            print("Reshaping the admin units file to the same src CRS")
            regions_gpd = regions_gpd.to_crs(src.crs)

    # PARALLEL MODE
    if mode == 0:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(create_country_mask_from_shapefile, regions_gpd.itertuples(), itertools.repeat(code), itertools.repeat(global_raster))
   
    # SERIAL MODE
    elif mode == 1:        
        for region in regions_gpd.itertuples():
            try:
                create_country_mask_from_shapefile(region, code, global_raster)
            except Exception as err:
                print("Error for : ", getattr(region, code))
                print(f"Unexpected {err=}, {type(err)=}")

    print("Job done.")
