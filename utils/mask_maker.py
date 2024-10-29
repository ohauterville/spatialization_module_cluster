# import fiona
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import pycountry

# import matplotlib.pyplot as plt
import numpy as np
import sys


def create_country_mask_from_shapefile(
    shapefile_filepath, corresponding_orthomosaic_filepath, iso3="FRA"
):
    """
    This function takes a GeoTIFF and a shapefile of administrative boundaries
    and clip the original GTIFF file along one country boundaries. To specify a country, one can
    provide its iso3 name.
    """
    Vector = gpd.read_file(shapefile_filepath)

    Vector = Vector[Vector["iso3"] == iso3]  # Subsetting to my AOI

    with rasterio.open(corresponding_orthomosaic_filepath) as src:
        Vector = Vector.to_crs(src.crs)
        # print(Vector.crs)
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

    output_file = output_path + iso3 + ".tif"

    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(out_image)

### MAIN
type = "POP"
year = "1990"

data_folder = "/data/mineralogie/hautervo/data/"
admin_units = data_folder + "admin_units/world_administrative_boundaries_countries/world-administrative-boundaries.shp"

raster_path = data_folder + "GHSL/Built_" + type + "/E" + year + "_100m_Global/"
global_raster = raster_path + "GHS_BUILT_" + type + "_E" + year + "_GLOBE_R2023A_54009_100_V1_0.tif"

output_path = raster_path + "subregions/"

if __name__ == "__main__":
    batch_size = 350
    if len(sys.argv) > 1:
        iteration_nb = int(sys.argv[1])
    else:
        iteration_nb = 0

    print("Starting...")
    for i in range(0, batch_size):
        country = list(pycountry.countries)[i + iteration_nb * batch_size]

        try:
            create_country_mask_from_shapefile(
                admin_units, global_raster, iso3=country.alpha_3
            )
            # print("Success for : ", country.alpha_3)
        except Exception as err:
            print("Error for : ", country.alpha_3)
            print(f"Unexpected {err=}, {type(err)=}")
    print("Job done.")
