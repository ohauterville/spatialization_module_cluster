import os
import time
import geopandas as gpd
import pandas as pd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm


def process_region(gadm_region, eubucco_gdf, region_id_col="GID_1"):
    """
    Clip EUBUCCO data with one GADM region and compute building areas.

    Args:
        gadm_region: GeoDataFrame row containing one GADM region
        eubucco_gdf: GeoDataFrame with EUBUCCO buildings
        region_id_col: Column name containing region IDs

    Returns:
        dict: Region information with calculated area
    """
    try:
        # Clip buildings to this region
        clipped = gpd.clip(eubucco_gdf, gadm_region.geometry)

        # Calculate area in projected CRS (ensure it's in meters)
        if not clipped.crs.is_projected:
            clipped = clipped.to_crs("EPSG:3035")  # LAEA Europe projection

        clipped["area_m2"] = clipped.geometry.area
        total_area = clipped["area_m2"].sum()

        return {
            "region_id": gadm_region[region_id_col],
            "region_name": gadm_region.get("NAME_1", ""),
            "building_count": len(clipped),
            "area_m2": total_area,
        }

    except Exception as e:
        print(f"Error processing region {gadm_region.get(region_id_col, '')}: {str(e)}")
        return None


def process_country(
    eubucco_path, gadm_path, output_csv, n_workers=None, country="BEL", lvl=1
):
    """
    Process one country file against GADM subnational regions.

    Args:
        eubucco_path: Path to EUBUCCO GPKG file
        gadm_path: Path to GADM GeoPackage/Shapefile
        output_csv: Path for output CSV
        n_workers: Number of parallel workers (default: all available CPUs)
    """
    start_time = time.time()

    # Load data with optimal settings
    print(f"[{time.strftime('%H:%M:%S')}] Loading datasets...")
    eubucco_gdf = gpd.read_file(eubucco_path, rows=100)  # Check first 1000 rows for CRS
    gadm_gdf = gpd.read_file(
        gadm_path, where=f"GID_{lvl-1}='{country}'", layer=f"ADM_{lvl}"
    )

    # Ensure compatible CRS
    if eubucco_gdf.crs != gadm_gdf.crs:
        print(
            f"[{time.strftime('%H:%M:%S')}] Reprojecting GADM data to match EUBUCCO CRS: {eubucco_gdf.crs}"
        )
        gadm_gdf = gadm_gdf.to_crs(eubucco_gdf.crs)

    # Now load full EUBUCCO dataset with proper CRS
    eubucco_gdf = gpd.read_file(eubucco_path)

    # Prepare parallel processing
    n_workers = min(n_workers or cpu_count() - 2, len(gadm_gdf))
    print(
        f"[{time.strftime('%H:%M:%S')}] Processing {len(gadm_gdf)} regions using {n_workers} workers..."
    )

    # Process regions in parallel
    with Pool(n_workers) as pool:
        tasks = [(row, eubucco_gdf) for _, row in gadm_gdf.iterrows()]
        results = list(tqdm(pool.starmap(process_region, tasks), total=len(tasks)))

    # Filter out failed regions
    valid_results = [r for r in results if r is not None]

    # Save results
    results_df = pd.DataFrame(valid_results)
    results_df.to_csv(output_csv, index=False)

    # Print summary
    duration = time.time() - start_time
    print(
        f"[{time.strftime('%H:%M:%S')}] \nProcessed {len(valid_results)}/{len(gadm_gdf)} regions"
    )
    print(
        f"[{time.strftime('%H:%M:%S')}] Total building area: {results_df['area_m2'].sum():,.2f} m²"
    )
    print(f"[{time.strftime('%H:%M:%S')}] Saved results to: {output_csv}")
    print(
        f"[{time.strftime('%H:%M:%S')}] Total processing time: {duration:.2f} seconds"
    )


if __name__ == "__main__":
    print(f"[{time.strftime('%H:%M:%S')}] Starting...")
    name = "FRA"
    lvl = 1
    data_folder = "/data/mineralogie/hautervo/data/"
    # Example OAR job configuration
    eubucco_path = (
        data_folder + "EUBUCCO/eubucco-v0_1/" + name + "/v0_1-" + name + ".gpkg"
    )  # EUBUCCO country file
    gadm_path = data_folder + "GADM/gadm_410-levels.gpkg"  # GADM admin1 boundaries
    output_csv = (
        data_folder
        + "EUBUCCO/eubucco-v0_1/"
        + name
        + "/"
        + "building_areas_per_region.csv"
    )

    # Adjust based on your OAR job resources
    n_workers = cpu_count() - 2

    process_country(
        eubucco_path, gadm_path, output_csv, n_workers, country=name, lvl=lvl
    )
