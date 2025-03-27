import os
import time
import pandas as pd
import geopandas as gpd
from tqdm import tqdm  # For progress bar


def calculate_total_building_area(folder_path, output_csv="building_areas.csv"):
    """
    Calculate the total area of buildings from all .shp files in a folder
    and save per-file results to a CSV.

    Args:
        folder_path (str): Path to the folder containing EUBUCCO shapefiles
        output_csv (str): Name of the output CSV file

    Returns:
        float: Total area in square meters
        str: Path to the created CSV file
    """
    results = []
    processed_files = 0
    start_time = time.time()

    # Get all shapefiles in the folder
    shapefiles = [
        f for f in os.listdir(folder_path) if f.endswith(".shp") or f.endswith(".gpkg")
    ]

    if not shapefiles:
        print("No shapefiles found in the directory.")
        return ""

    print(f"Found {len(shapefiles)} shapefiles to process...")

    for shp_file in tqdm(shapefiles, desc="Processing shapefiles"):
        file_path = os.path.join(folder_path, shp_file)
        try:
            # Read only necessary columns to save memory
            gdf = gpd.read_file(file_path, columns=["geometry"])

            # Ensure we're working with the correct CRS (EPSG:3035 is common for EUBUCCO)
            if gdf.crs is None:
                print(f"Warning: No CRS defined in {shp_file}, assuming EPSG:3035")
                gdf = gdf.set_crs("EPSG:3035")

            # Convert to meter-based CRS if not already
            if not gdf.crs.is_projected:
                gdf = gdf.to_crs("EPSG:3035")  # LAEA Europe projection

            # Calculate area in square meters
            gdf["area_m2"] = gdf.geometry.area
            file_area = gdf["area_m2"].sum()

            results.append({"filename": shp_file, "area_m2": file_area})
            processed_files += 1

            # Explicit cleanup
            del gdf

        except Exception as e:
            print(f"Error processing {shp_file}: {str(e)}")
            continue

    # Save results to CSV
    results_df = pd.DataFrame(results)
    csv_path = os.path.join(folder_path, output_csv)
    results_df.to_csv(csv_path, index=False)

    end_time = time.time()
    print(
        f"\nProcessed {processed_files}/{len(shapefiles)} files in {end_time - start_time:.2f} seconds"
    )
    print(f"Per-file results saved to: {csv_path}")

    return csv_path


# Example usage
if __name__ == "__main__":
    region = "BEL"

    data_folder = "/data/mineralogie/hautervo/data/"
    folder_path = data_folder + "EUBUCCO/eubucco-v0_1/FRA/"
    # folder_path = data_folder + "EUBUCCO/eubucco-v0_1/" + region + "/subregions/"

    csv_path = calculate_total_building_area(folder_path)

    # Optionally print the CSV contents
    print("\nFirst few rows of the results:")
    print(pd.read_csv(csv_path).head())
