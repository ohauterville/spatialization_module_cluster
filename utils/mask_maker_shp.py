import geopandas as gpd
import dask_geopandas as dgpd
import fiona

# import dask
import dask.dataframe as dd

# from dask import compute
import os

# import gc
import time
import psutil
import logging


def clip_subregion(partition, subregion):
    """Clips a single subregion and returns a GeoDataFrame"""
    try:
        # Clip the region using the source raster
        clipped = partition.clip(subregion.geometry)

        # Return the clipped data as a GeoDataFrame (for Dask to handle)
        return clipped

    except Exception as e:
        print(
            f"[{time.strftime('%H:%M:%S')}] ❌ Error clipping {subregion[subregion_col]}: {e}"
        )
        return None


##### MAIN #####
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(f"[{time.strftime('%H:%M:%S')}] Starting main function...")
    print(f"[{time.strftime('%H:%M:%S')}] Available CPU cores: {os.cpu_count()}")
    print(
        f"[{time.strftime('%H:%M:%S')}] Available memory: {psutil.virtual_memory().total / (1024**3)} GB"
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

    n_workers = min(os.cpu_count() - 2, 8)

    # Read source file with Dask
    print(f"[{time.strftime('%H:%M:%S')}] Reading src file from {shp_file}...")
    src = dgpd.read_file(shp_file, npartitions=n_workers)
    src = src.spatial_shuffle()  # Shuffle for better partitioning
    src = src.persist()  # Keep the data in memory
    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")

    # Read subregions with Geopandas
    print(
        f"[{time.strftime('%H:%M:%S')}] Reading admin units file from {admin_units}..."
    )
    subregions_gpd = gpd.read_file(
        admin_units, layer=layer, where=f"{parent_col}='{parent_key}'"
    )
    subregions_gpd = subregions_gpd[subregions_gpd["geometry"].is_valid]

    # Ensure CRS consistency
    if subregions_gpd.crs != src.crs:
        subregions_gpd = subregions_gpd.to_crs(src.crs)

    print(f"[{time.strftime('%H:%M:%S')}] Reading done.")

    # Submit Tasks Using map_partitions
    results = []
    for _, subregion in subregions_gpd.iterrows():
        result = src.map_partitions(clip_subregion, subregion)
        results.append(result)

    # Concatenate all results into a single Dask GeoDataFrame
    clipped = dd.concat(results)

    # Persist to memory (triggers computation)
    clipped = clipped.persist()

    # Save files individually
    for _, subregion in subregions_gpd.iterrows():
        subregion_name = subregion[subregion_col]
        output_file = output_path + subregion_name + ".shp"

        if not os.path.isfile(output_file):
            print(f"[{time.strftime('%H:%M:%S')}] Saving {output_file}")

            # Compute and filter based on geometry intersection
            filtered = clipped.compute()
            filtered[filtered.intersects(subregion.geometry)].to_file(output_file)

            print(f"[{time.strftime('%H:%M:%S')}] ✅ Saved {output_file}")

    print(f"[{time.strftime('%H:%M:%S')}] ✅ Job completed.")
