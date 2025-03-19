import geopandas as gpd
import dask_geopandas as dgpd
import fiona

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import itertools
import os
import gc
import time


def make_subregional_mask(
    src,
    subregion,
    subregion_col: str,
    subregions_crs,
    cpu_per_partition: int,
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
            print(f"[{time.strftime('%H:%M:%S')}] Reading src file from {shp_file}...")
            src = dgpd.read_file(shp_file, npartitions=cpu_per_partition)
            print(f"[{time.strftime('%H:%M:%S')}] Reading done.")

            subregion_gdf = gpd.GeoDataFrame(
                geometry=[subregion.geometry], crs=subregions_crs
            )

            if subregion_gdf.crs != src.crs:
                print(f"[{time.strftime('%H:%M:%S')}] Reprojecting...")
                subregion_gdf.to_crs(src.crs, inplace=True)
                print(f"[{time.strftime('%H:%M:%S')}] Reprojection done.")
            # clipped_gdf = gpd.clip(src, subregion_gdf)

            # Perform the clip operation using Dask-GeoPandas
            clipped = src.map_partitions(gpd.clip, subregion_gdf)

            # Trigger computation and convert to a GeoDataFrame (if needed)
            clipped_gdf = clipped.compute()

            os.makedirs(os.path.dirname(output_file), exist_ok="True")
            clipped_gdf.to_file(output_file)
            print(f"[{time.strftime('%H:%M:%S')}] Successfully saved ", output_file)

            del subregion, subregion_gdf, clipped_gdf
            gc.collect()
        except Exception as e:
            print(e)

    else:
        print("File already exists: ", output_file)
        del subregion
        gc.collect()


##### MAIN #####
if __name__ == "__main__":
    # Get the path to the node file from the OAR environment variable
    node_file = os.environ.get("OAR_NODEFILE")

    if node_file:
        # Read the node file to count the number of nodes
        with open(node_file, "r") as f:
            nodes = f.readlines()
        n_nodes = len(nodes)
    else:
        # If not running in an OAR job, assume 1 node
        n_nodes = 1

    n_cores = max(1, n_nodes * os.cpu_count() - 2)
    print(f"[{time.strftime('%H:%M:%S')}] Starting with {n_cores} CPU cores...")
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
    print(
        f"[{time.strftime('%H:%M:%S')}] Reading admin units file from {admin_units}..."
    )
    subregions_gpd = gpd.read_file(
        admin_units, layer=layer, where=f"{parent_col}='{parent_key}'"
    )
    subregions_crs = subregions_gpd.crs
    # some safety checks
    subregions_gpd = subregions_gpd[~subregions_gpd["geometry"].is_empty]
    subregions_gpd = subregions_gpd[~subregions_gpd["geometry"].isna()]
    subregions_gpd = subregions_gpd[subregions_gpd["geometry"].is_valid]

    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")

    # PARALLEL MODE
    if mode == 0:
        print(f"[{time.strftime('%H:%M:%S')}] Starting parallel computing...")
        rows = list(subregions_gpd.iterrows())
        n_subregions = min(len(rows), n_cores)
        n_cpu_per_partition = max(1, int(n_cores / n_subregions))
        print(
            f"[{time.strftime('%H:%M:%S')}] Using {n_cpu_per_partition} CPUs per subregion"
        )

        with ProcessPoolExecutor(max_workers=n_subregions) as executor:
            executor.map(
                make_subregional_mask,
                itertools.repeat(shp_file),
                (row for _, row in rows),
                itertools.repeat(subregion_col),
                itertools.repeat(subregions_crs),
                itertools.repeat(n_cpu_per_partition),
            )

    # SERIAL MODE
    elif mode == 1:
        pass

    print("Job done.")
