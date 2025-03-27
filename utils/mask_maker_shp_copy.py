import geopandas as gpd
import dask_geopandas as dgpd
import fiona

import dask
from dask import delayed, compute
from dask.distributed import LocalCluster, Client

# from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# import itertools
import os
import gc
import time
import psutil
import logging

"""
This function is made to be run on a OAR cluster passive job only ! 
"""


def make_subregional_mask(
    src,
    subregion,
    subregion_col: str,
    subregions_crs,
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

            # subregion_gdf = gpd.GeoDataFrame(
            #     geometry=[subregion.geometry], crs=subregions_crs
            # )

            print(f"[{time.strftime('%H:%M:%S')}] Processing {subregion_name}")
            clipped = src.clip(subregion.geometry)

            os.makedirs(os.path.dirname(output_file), exist_ok="True")
            clipped.to_file(output_file)
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
    logging.basicConfig(level=logging.DEBUG)
    print(f"[{time.strftime('%H:%M:%S')}] Starting main function...")
    print(f"[{time.strftime('%H:%M:%S')}] Available CPU cores: ", os.cpu_count())
    print(
        f"[{time.strftime('%H:%M:%S')}] Available memory: {psutil.virtual_memory().total / (1024**3)}GB"
    )
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

    #####
    dask.config.set(
        {"distributed.worker.memory.spill": 0.8}
    )  # Spill at 80% memory usage
    dask.config.set(
        {"distributed.worker.memory.target": 0.6}
    )  # Try to keep memory below 60%
    dask.config.set(
        {"distributed.worker.memory.terminate": 0.95}
    )  # Terminate above 95% (last resort)
    dask.config.set({"distributed.comm.timeouts.connect": "300s"})
    dask.config.set({"distributed.comm.timeouts.tcp": "300s"})

    ###########################################
    # Get the path to the node file from the OAR environment variable
    node_file = os.environ.get("OAR_NODEFILE")
    n_nodes = len(open(node_file).readlines()) if node_file else 1
    n_workers = min(os.cpu_count(), 4)  # Limit workers to avoid oversubscription
    max_memory = 4

    # Initialize OARCluster in passive mode
    os.environ["PATH"] = f"{os.environ['HOME']}/venv/bin:" + os.environ["PATH"]

    print(f"[{time.strftime('%H:%M:%S')}] Starting LocalCluster instanciation...")
    cluster = LocalCluster(
        n_workers=n_workers,  # Cores per node
        threads_per_worker=1,  # Keep threads low
        memory_limit=f"{max_memory}GB",  # Use 16GB memory
        # memory_limit=f"{int(psutil.virtual_memory().total * 0.75 / (1024**3))}GB",  # Use 75% of memory
        processes=True,  # Processes per node
        dashboard_address=":8787",  # Accessible on localhost:8787
        local_directory="/tmp/dask",
    )
    print(f"[{time.strftime('%H:%M:%S')}] Done.")

    print(f"[{time.strftime('%H:%M:%S')}] Starting connecting to the client...")
    # Connect to the cluster
    client = Client(cluster)
    print(
        f"[{time.strftime('%H:%M:%S')}] Dask Dashboard available at:",
        cluster.dashboard_link,
    )

    print(f"[{time.strftime('%H:%M:%S')}] Reading src file from {shp_file}...")
    src = dgpd.read_file(shp_file, npartitions=n_workers)
    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")
    # #### Spatial Shuffle for Better Partitioning ####
    # src = src.spatial_shuffle()  # Spatially shuffle
    # src = src.persist()

    print(
        f"[{time.strftime('%H:%M:%S')}] Reading admin units file from {admin_units}..."
    )
    subregions_gpd = gpd.read_file(
        admin_units, layer=layer, where=f"{parent_col}='{parent_key}'"
    )
    subregions_crs = subregions_gpd.crs
    # some safety checks
    subregions_gpd = subregions_gpd[subregions_gpd["geometry"].is_valid]
    # CRS Check
    if subregions_gpd.crs != src.crs:
        subregions_gpd = subregions_gpd.to_crs(src.crs)
    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")
    subregions = [row for _, row in subregions_gpd.iterrows()]

    # Submit Tasks
    tasks = [
        delayed(make_subregional_mask)(src, row, subregion_col, src.crs)
        for row in subregions
    ]
    compute(tasks)

    print(f"[{time.strftime('%H:%M:%S')}] ✅ Job completed.")
    client.close()
