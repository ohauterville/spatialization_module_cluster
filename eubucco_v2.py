import geopandas as gpd
import pandas as pd
import os
import logging
import time

# --- Configuration ---
# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# --- Helper Function ---
def sanitize_filename(name):
    """Removes or replaces characters problematic for filenames."""
    # Replace spaces and slashes with underscores
    name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    # Remove other potentially problematic characters (add more if needed)
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        name = name.replace(char, "")
    return name


# --- Main Processing Function ---
def split_eubucco_by_region_via_csv(
    eubucco_gpkg_path: str,
    eubucco_csv_path: str,
    gadm_gpkg_path: str,
    output_dir: str,
    country_iso_code: str = "FRA",
    eubucco_id_col_gpkg: str = "building_id",  # Column name in the main GPKG
    eubucco_id_col_csv: str = "id",  # Column name in the CSV (adjust if needed)
    gadm_level: int = 1,
):
    """
    Splits a large EU-BUCCO GeoPackage for a country into regional GeoPackages
    using GADM boundaries and matching building IDs from an auxiliary CSV.

    Args:
        eubucco_gpkg_path (str): Path to the main EU-BUCCO GeoPackage with geometries.
        eubucco_csv_path (str): Path to the EU-BUCCO CSV with building attributes (incl. IDs).
        gadm_gpkg_path (str): Path to the GADM GeoPackage containing administrative boundaries.
        output_dir (str): Directory to save the split regional GeoPackage files.
        country_iso_code (str): ISO 3166-1 alpha-3 code for the country (e.g., "FRA").
        eubucco_id_col_gpkg (str): Name of the building ID column in the EU-BUCCO GPKG.
        eubucco_id_col_csv (str): Name of the building ID column in the EU-BUCCO CSV.
                                   *Crucial Assumption*: This ID contains the region code.
        gadm_level (int): GADM administrative level to split by (e.g., 1 for regions).
    """
    start_time_total = time.time()

    # 1. Validate Inputs and Create Output Directory
    logging.info("Starting EU-BUCCO regional split process.")
    if not os.path.exists(eubucco_gpkg_path):
        logging.error(f"EU-BUCCO GeoPackage not found: {eubucco_gpkg_path}")
        raise FileNotFoundError(f"EU-BUCCO GeoPackage not found: {eubucco_gpkg_path}")
    if not os.path.exists(eubucco_csv_path):
        logging.error(f"EU-BUCCO CSV not found: {eubucco_csv_path}")
        raise FileNotFoundError(f"EU-BUCCO CSV not found: {eubucco_csv_path}")
    if not os.path.exists(gadm_gpkg_path):
        logging.error(f"GADM GeoPackage not found: {gadm_gpkg_path}")
        raise FileNotFoundError(f"GADM GeoPackage not found: {gadm_gpkg_path}")

    try:
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Output directory: {output_dir}")
    except OSError as e:
        logging.error(f"Failed to create output directory {output_dir}: {e}")
        raise

    # 2. Load GADM Administrative Boundaries
    try:
        logging.info(f"Loading GADM boundaries from: {gadm_gpkg_path}")
        gadm_gdf = gpd.read_file(
            gadm_gpkg_path,
            where=f"GID_{gadm_level-1}='{country_iso_code}'",
            layer=f"ADM_{gadm_level}",
        )
        # Filter for the specified country and GADM level
        gadm_level_col = f"GID_{gadm_level}"
        gadm_name_col = f"NAME_{gadm_level}"
        if (
            gadm_level_col not in gadm_gdf.columns
            or gadm_name_col not in gadm_gdf.columns
        ):
            raise ValueError(
                f"GADM file missing required columns: {gadm_level_col} or {gadm_name_col}"
            )

        country_regions = gadm_gdf[
            (gadm_gdf[f"GID_{gadm_level-1}"] == country_iso_code)
            & (gadm_gdf[gadm_level_col].notna())
        ].copy()  # Use .copy() to avoid SettingWithCopyWarning

        if country_regions.empty:
            logging.error(
                f"No GADM level {gadm_level} regions found for country {country_iso_code}."
            )
            raise ValueError(
                f"No GADM level {gadm_level} regions found for country {country_iso_code}."
            )

        logging.info(
            f"Found {len(country_regions)} GADM level {gadm_level} regions for {country_iso_code}."
        )
        # Ensure GADM CRS is consistent if needed later, but not strictly necessary for this logic
        # expected_gadm_crs = eubucco_gdf.crs # Example if matching needed
        # if country_regions.crs != expected_gadm_crs:
        #    logging.warning(f"Reprojecting GADM CRS from {country_regions.crs} to {expected_gadm_crs}")
        #    country_regions = country_regions.to_crs(expected_gadm_crs)

    except Exception as e:
        logging.error(f"Error loading or processing GADM data: {e}")
        raise

    # 3. Load EU-BUCCO CSV (Attributes and IDs)
    #    This might still be large, consider chunking if memory is an issue
    try:
        logging.info(f"Loading EU-BUCCO CSV from: {eubucco_csv_path}")
        # Use low_memory=False if DtypeWarnings occur, or specify dtypes explicitly
        eubucco_df = pd.read_csv(eubucco_csv_path, low_memory=False)
        if eubucco_id_col_csv not in eubucco_df.columns:
            raise ValueError(
                f"EU-BUCCO CSV missing required ID column: {eubucco_id_col_csv}"
            )

        # --- Crucial Step: Extract Region Code from CSV ID --- # <<< RE-MODIFIED PART
        # *Assumption*: The region code is the first number after 'COUNTRY_ISO.'
        # Example: 'v0.1-LUX.3.4.8_1-934' -> needs '3'
        logging.info(
            f"Extracting region code from CSV column '{eubucco_id_col_csv}' based on format 'COUNTRY_ISO.X...'"
        )
        try:
            # Ensure the ID column is string type before splitting
            id_series = eubucco_df[eubucco_id_col_csv].astype(str)

            # 1. Split by '-' and take the second part (e.g., 'LUX.3.4.8_1')
            parts_after_version = id_series.str.split("-", n=1).str[
                1
            ]  # n=1 ensures only first '-' is used

            # Check for NaNs resulting from split errors
            parts_after_version.fillna(
                "", inplace=True
            )  # Fill NaN to prevent errors in next step
            if (parts_after_version == "").any():
                logging.warning(
                    f"Some IDs in '{eubucco_id_col_csv}' might not contain '-' separator or content after it. Review data."
                )

            # 2. Split the result by '.' (e.g., ['LUX', '3', '4', '8_1'])
            admin_parts = parts_after_version.str.split(".")

            # 3. Extract the *second element* (index 1) - this should be the region code
            #    Example: 'LUX.3.4.8_1' -> split -> ['LUX', '3', '4', '8_1'] -> take element 1 -> '3'
            #    Use .get(1) to safely handle lists that might be too short (returns None)
            region_code_str = admin_parts.str.get(1)

            # Check for potential None values (due to .get or if admin_parts itself was None/NaN)
            valid_indices = region_code_str.notna() & (region_code_str != "")
            if not valid_indices.all():
                num_invalid = len(eubucco_df) - valid_indices.sum()
                logging.warning(
                    f"{num_invalid} IDs might not follow the 'COUNTRY_ISO.X...' format after the first '-'. They will not be assigned a region code. Review data."
                )

            # Assign the extracted code
            eubucco_df["region_code_from_id"] = None  # Initialize
            eubucco_df.loc[valid_indices, "region_code_from_id"] = region_code_str[
                valid_indices
            ]

            # Log summary
            num_processed = valid_indices.sum()
            num_total = len(eubucco_df)
            if num_processed < num_total:
                logging.warning(
                    f"Successfully extracted region codes for {num_processed}/{num_total} buildings. {num_total - num_processed} had an unexpected ID format or missing parts."
                )
            else:
                logging.info(
                    f"Extracted 'region_code_from_id' (e.g., '3') from all {num_total} CSV IDs."
                )

            # Optional: Inspect unique codes extracted
            unique_codes_found = eubucco_df["region_code_from_id"].dropna().unique()
            logging.info(
                f"Unique region codes found in CSV IDs: {sorted(list(unique_codes_found))}"
            )

        except KeyError:
            logging.error(f"Failed to access ID column '{eubucco_id_col_csv}' in CSV.")
            raise
        # Note: IndexError should be less likely with .str.get(), but keeping general Exception
        except Exception as e:
            logging.error(
                f"Error extracting region code from CSV ID: {e}", exc_info=True
            )  # Log traceback
            raise

        # Create a set of unique region codes found in the CSV for faster lookup (excluding None/NaN)
        csv_region_codes = set(eubucco_df["region_code_from_id"].dropna().unique())
        if not csv_region_codes:
            logging.error(
                "No valid region codes could be extracted from the CSV IDs. Stopping."
            )
            raise ValueError("Failed to extract any region codes from CSV IDs.")
        logging.info(
            f"Found {len(csv_region_codes)} unique valid region codes in CSV IDs for matching."
        )

    except Exception as e:
        logging.error(f"Error loading or processing EU-BUCCO CSV: {e}")
        raise

    # 4. Load EU-BUCCO GeoPackage (Geometries and IDs)
    #    This is the largest file, loading it entirely requires significant RAM.
    #    If this fails due to memory, you might need dask-geopandas or iterate differently.
    try:
        logging.info(
            f"Loading EU-BUCCO GeoPackage from: {eubucco_gpkg_path} (This may take time/memory)"
        )
        start_load_gpkg = time.time()
        eubucco_gdf = gpd.read_file(eubucco_gpkg_path)
        end_load_gpkg = time.time()
        logging.info(
            f"Loaded EU-BUCCO GeoPackage in {end_load_gpkg - start_load_gpkg:.2f} seconds."
        )

        if eubucco_id_col_gpkg not in eubucco_gdf.columns:
            raise ValueError(
                f"EU-BUCCO GPKG missing required ID column: {eubucco_id_col_gpkg}"
            )

        # Optional: Set index for potentially faster lookups later if needed,
        # though merge might handle this internally. Requires testing on full data.
        # logging.info("Setting index on EU-BUCCO GPKG ID column...")
        # eubucco_gdf = eubucco_gdf.set_index(eubucco_id_col_gpkg, drop=False)
        # logging.info("Index set.")

    except Exception as e:
        logging.error(f"Error loading EU-BUCCO GeoPackage: {e}. Consider memory usage.")
        raise

    # 5. Iterate Through Regions, Filter CSV, Join Geometries, and Save
    logging.info("Starting regional splitting...")
    processed_regions = 0
    skipped_regions_no_buildings = 0

    for index, region in country_regions.iterrows():
        region_gid = region[gadm_level_col]
        region_name = region[gadm_name_col]
        sanitized_region_name = sanitize_filename(region_name)
        region_process_start_time = time.time()

        logging.info(
            f"--- Processing GADM Region: {region_name} (GID: {region_gid}) ---"
        )

        # --- Determine the corresponding region code format from GADM --- # <<< RE-MODIFIED PART
        # GADM GID_1 format is often like 'COUNTRY.X_suffix' (e.g., 'LUX.3_1').
        # We need to extract the 'X' part (e.g., '3') to match the format
        # extracted from the eubucco ID (e.g., '3').
        target_region_code = None  # Initialize
        try:
            # Ensure region_gid is a string before splitting
            if not isinstance(region_gid, str):
                raise TypeError(
                    f"Expected GID to be a string, but got {type(region_gid)}"
                )

            # Example: 'LUX.3_1'
            gid_parts = region_gid.split(".")
            if len(gid_parts) > 1:
                code_with_suffix = gid_parts[1]  # e.g., '3_1'
                # Now split by '_' and take the first part
                region_code_parts = code_with_suffix.split("_")
                if len(region_code_parts) > 0:
                    target_region_code = region_code_parts[0]  # e.g., '3'
                    logging.info(
                        f"Target region code derived from GADM GID '{region_gid}': {target_region_code}"
                    )
                else:
                    # This case implies the part after '.' was empty or only '_'
                    raise ValueError(
                        f"Could not extract code before '_' from '{code_with_suffix}'"
                    )
            else:
                # Handle cases where the GID might not have a dot
                raise ValueError(
                    f"GID format '{region_gid}' unexpected, does not contain '.'"
                )

        except (IndexError, ValueError, TypeError) as e:
            logging.warning(
                f"Could not parse GADM GID '{region_gid}' to expected format 'COUNTRY.X_suffix' for region {region_name}. Error: {e}. Skipping."
            )
            continue  # Skip to the next region

        # Check if a valid target code was derived
        if target_region_code is None or target_region_code == "":
            logging.warning(
                f"Failed to derive a valid target region code for GID '{region_gid}'. Skipping region {region_name}."
            )
            continue

        # Check if this region code exists in the set of codes extracted from the CSV
        if target_region_code not in csv_region_codes:
            logging.warning(
                f"Region code '{target_region_code}' (derived from GADM for {region_name}) not found among codes extracted from CSV building IDs {csv_region_codes}. Skipping."
            )
            skipped_regions_no_buildings += 1
            continue

        # Filter the CSV DataFrame for buildings matching the current region code
        logging.info(f"Filtering CSV for region code '{target_region_code}'...")
        # Ensure we handle potential None/NaN values from the extraction step if any occurred
        buildings_in_region_df = eubucco_df[
            (eubucco_df["region_code_from_id"] == target_region_code)
            & (eubucco_df["region_code_from_id"].notna())  # Explicitly check for notna
        ].copy()  # Use .copy() to avoid SettingWithCopyWarning

        if buildings_in_region_df.empty:
            logging.warning(
                f"No buildings found in CSV for region {region_name} (code '{target_region_code}') after filtering. Skipping."
            )
            skipped_regions_no_buildings += 1
            continue
        else:
            logging.info(
                f"Found {len(buildings_in_region_df)} building records in CSV for {region_name}."
            )

        # Select only the necessary ID column for joining
        building_ids_for_region = buildings_in_region_df[[eubucco_id_col_csv]].copy()
        # Rename CSV ID column to match GPKG ID column for the merge
        building_ids_for_region.rename(
            columns={eubucco_id_col_csv: eubucco_id_col_gpkg}, inplace=True
        )

        # Merge (Inner Join) the geometries (eubucco_gdf) with the filtered IDs
        logging.info(f"Merging geometries with filtered IDs for {region_name}...")
        start_merge_time = time.time()
        try:
            # Check data types before merge if issues arise
            gpkg_id_type = eubucco_gdf[eubucco_id_col_gpkg].dtype
            csv_id_type = building_ids_for_region[eubucco_id_col_gpkg].dtype
            if gpkg_id_type != csv_id_type:
                logging.warning(
                    f"Mismatched ID types for merge: GPKG is {gpkg_id_type}, CSV (filtered) is {csv_id_type}. Attempting conversion..."
                )
                # Decide conversion strategy - often safer to convert both to string if unsure
                eubucco_gdf[eubucco_id_col_gpkg] = eubucco_gdf[
                    eubucco_id_col_gpkg
                ].astype(str)
                building_ids_for_region[eubucco_id_col_gpkg] = building_ids_for_region[
                    eubucco_id_col_gpkg
                ].astype(str)
                # Alternatively, convert CSV to match GPKG:
                # building_ids_for_region[eubucco_id_col_gpkg] = building_ids_for_region[eubucco_id_col_gpkg].astype(gpkg_id_type)

            region_gdf = eubucco_gdf.merge(
                building_ids_for_region,
                on=eubucco_id_col_gpkg,
                how="inner",
            )
        except Exception as e:
            logging.error(
                f"Error during merge for region {region_name} (code '{target_region_code}'): {e}. Check ID matching and data types. Skipping region."
            )
            continue  # Skip to the next region
        end_merge_time = time.time()
        logging.info(
            f"Merge completed in {end_merge_time - start_merge_time:.2f} seconds."
        )

        if region_gdf.empty:
            logging.warning(
                f"Merge resulted in zero buildings for region {region_name} (code '{target_region_code}'). This indicates IDs from CSV (for this region) were not found in the GPKG ID column '{eubucco_id_col_gpkg}'. Check data consistency. Skipping save."
            )
            skipped_regions_no_buildings += 1
            continue
        else:
            logging.info(
                f"Successfully merged {len(region_gdf)} buildings with geometries for {region_name}."
            )

        # Define output path and save the regional GeoPackage
        output_filename = f"{country_iso_code}.{target_region_code}_1.gpkg"
        output_filepath = os.path.join(output_dir, output_filename)

        logging.info(f"Saving region {region_name} to: {output_filepath}")
        start_save_time = time.time()
        try:
            region_gdf.to_file(output_filepath, driver="GPKG")
            end_save_time = time.time()
            logging.info(
                f"Successfully saved {output_filename} in {end_save_time - start_save_time:.2f} seconds."
            )
            processed_regions += 1
        except Exception as e:
            logging.error(f"Failed to save GeoPackage for region {region_name}: {e}")

        region_process_end_time = time.time()
        logging.info(
            f"Finished processing {region_name} in {region_process_end_time - region_process_start_time:.2f} seconds.\n"
        )
        # Optional memory management
        # del region_gdf, buildings_in_region_df, building_ids_for_region
        # import gc
        # gc.collect()

    # 6. Final Summary
    end_time_total = time.time()
    logging.info("=" * 30)
    logging.info("Regional Split Process Completed.")
    logging.info(
        f"Total execution time: {(end_time_total - start_time_total) / 60:.2f} minutes."
    )
    logging.info(f"Successfully processed and saved {processed_regions} regions.")
    logging.info(
        f"Skipped {skipped_regions_no_buildings} regions (no buildings found in CSV/Merge)."
    )
    logging.info(f"Output files are located in: {output_dir}")
    logging.info("=" * 30)


# --- Example Usage ---
if __name__ == "__main__":
    # ----- USER: Define your paths here -----
    country_iso_code = "FRA"
    data_folder = "/data/mineralogie/hautervo/data/"
    PATH_TO_EUBUCCO_FRANCE_GPKG = os.path.join(
        data_folder,
        f"EUBUCCO/eubucco-v0_1/{country_iso_code}/v0_1-{country_iso_code}.gpkg",
    )
    PATH_TO_EUBUCCO_CSV = os.path.join(
        data_folder,
        f"EUBUCCO/eubucco-v0_1/{country_iso_code}/v0_1-{country_iso_code}.csv",
    )
    PATH_TO_GADM_GPKG = os.path.join(data_folder, "GADM/gadm_410-levels.gpkg")
    OUTPUT_DIRECTORY = os.path.join(
        data_folder, f"EUBUCCO/eubucco-v0_1/{country_iso_code}/subregions"
    )

    # ----- Adjust column names if different -----
    EUBUCCO_ID_COLUMN_GPKG = "id"  # Default for v1 was 'id' - CHECK YOUR FILE
    EUBUCCO_ID_COLUMN_CSV = "id"  # Default for v1 was 'id' - CHECK YOUR FILE

    # ----- Run the process -----
    try:
        split_eubucco_by_region_via_csv(
            eubucco_gpkg_path=PATH_TO_EUBUCCO_FRANCE_GPKG,
            eubucco_csv_path=PATH_TO_EUBUCCO_CSV,
            gadm_gpkg_path=PATH_TO_GADM_GPKG,
            output_dir=OUTPUT_DIRECTORY,
            country_iso_code=country_iso_code,  # ISO code for France
            eubucco_id_col_gpkg=EUBUCCO_ID_COLUMN_GPKG,
            eubucco_id_col_csv=EUBUCCO_ID_COLUMN_CSV,
            gadm_level=1,  # GADM level for regions in France
        )
    except FileNotFoundError as fnf_error:
        logging.error(f"Input file not found: {fnf_error}")
    except ValueError as val_error:
        logging.error(f"Data error: {val_error}")
    except Exception as general_error:
        logging.error(
            f"An unexpected error occurred: {general_error}", exc_info=True
        )  # Log traceback
