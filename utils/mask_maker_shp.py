import geopandas as gpd
import dask_geopandas as dgpd
import fiona

from concurrent.futures import ProcessPoolExecutor
import itertools
import os
import time


def make_subregional_mask(
    src,
    subregion,
    subregion_col: str,
    crs,
):
    """
    This function takes a GeoTIFF and a shapefile of administrative boundaries
    and clip the original GTIFF file along one country boundaries. To specify a country, one can
    provide its iso3 name.
    """
    subregion_name = subregion[subregion_col]
    output_file = output_path + subregion_name + ".shp"

    if not os.path.isfile(output_file):
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Starting ", subregion_name)
            subregion_gdf = gpd.GeoDataFrame(geometry=[subregion.geometry], crs=crs)
            clipped_gdf = gpd.clip(src, subregion_gdf)

            os.makedirs(os.path.dirname(output_file), exist_ok="True")
            clipped_gdf.to_file(output_file)
            print(f"[{time.strftime('%H:%M:%S')}] Successfully saved ", output_file)
        except Exception as e:
            print(e)

    else:
        print("File already exists: ", output_file)


##### MAIN #####
if __name__ == "__main__":
    max_workers = 16
    lvl = 1
    data_folder = "/data/mineralogie/hautervo/data/"
    admin_units = data_folder + "GADM/gadm_410-levels.gpkg"
    layers = fiona.listlayers(admin_units)
    layer = layers[lvl]
    parent_col = f"GID_{lvl-1}"
    subregion_col = f"GID_{lvl}"

    parent_key = "BEL"

    shp_path = data_folder + f"EUBUCCO/eubucco-v0_1/{parent_key}/"
    shp_file = shp_path + f"v0_1-{parent_key}.gpkg"
    output_path = shp_path + "subregions/"

    mode = 0  # 0 for parallel, 1 for serial

    ###########################################
    print(f"[{time.strftime('%H:%M:%S')}] Reading src file from {shp_file}...")
    src = dgpd.read_file(shp_file, npartitions=max_workers).compute()
    print("Done.")

    print(
        f"[{time.strftime('%H:%M:%S')}] Reading admin units file from {admin_units}..."
    )
    subregions_gpd = gpd.read_file(
        admin_units, layer=layer, where=f"{parent_col}='{parent_key}'"
    )
    # some safety checks
    subregions_gpd = subregions_gpd[~subregions_gpd["geometry"].is_empty]
    subregions_gpd = subregions_gpd[~subregions_gpd["geometry"].isna()]
    subregions_gpd = subregions_gpd[subregions_gpd["geometry"].is_valid]

    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")

    if subregions_gpd.crs != src.crs:
        print(f"[{time.strftime('%H:%M:%S')}] Reprojecting...")
        subregions_gpd.to_crs(src.crs, inplace=True)
        print(f"[{time.strftime('%H:%M:%S')}] Reprojection done...")

    # PARALLEL MODE
    if mode == 0:
        print(f"[{time.strftime('%H:%M:%S')}] Starting parallel computing...")
        rows = list(subregions_gpd.iterrows())
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            executor.map(
                make_subregional_mask,
                itertools.repeat(src),
                (row for _, row in rows),
                itertools.repeat(subregion_col),
                itertools.repeat(src.crs),
            )

    # SERIAL MODE
    elif mode == 1:
        pass
        # for country in pycountry.countries:
        #     try:
        #         make_subregional_mask(admin_units_gpd, src, country)
        #     except Exception as err:
        #         print("Error for : ", country.alpha_3)
        #         print(f"Unexpected {err=}, {type(err)=}")

    print("Job done.")
