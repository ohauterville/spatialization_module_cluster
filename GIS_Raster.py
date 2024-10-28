from GIS import GIS

import os
import sys
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import mapping


class GIS_Raster(GIS):
    def __init__(self, file, name, year, lvl):
        super().__init__(name, year, lvl)

        if os.path.exists(file):
            if file.endswith(".tif"):
                self.file = file
                self.type = "raster"
                self.year = year
                self.lvl = lvl
            else:
                print(
                    "The file: ", file, " seems to be neither a raster. Please check the given file."
                )
                sys.exit()
        else:
            print("The file: ", file, " does not exists. Check the path.")
            sys.exit()

    def make_mask(
        self,
        shapefile,
        region_name: str,
        region_col_name: str,
        parent_name: str,
        overwrite=False,
    ):

        # Read the raster file
        with rasterio.open(self.file) as src:
            for index, row in shapefile.iterrows():
                if row[region_col_name] == region_name:
                    # Define the output raster path
                    subregions_file = os.path.join(
                        os.path.dirname(self.file),
                        os.path.join(parent_name, "subregions"),
                        f"{region_name}.tif",
                    )
                    os.makedirs(os.path.dirname(subregions_file), exist_ok=True)

                    # check if the file already exists
                    if not os.path.isfile(subregions_file) or overwrite:
                        # Ensure the shapefile geometry is in the same coordinate system as the raster
                        if shapefile.crs != src.crs:
                            print(
                                "Warning the CRS do not match! The code below is not working for now"
                            )
                            shapefile = shapefile.to_crs(src.crs)
                            shape = [
                                mapping(
                                    shapefile.loc[
                                        shapefile[region_col_name] == region_name
                                    ].geometry
                                )
                            ]
                        else:
                            shape = [mapping(row.geometry)]

                        try:
                            # Mask the raster with the individual shape
                            out_image, out_transform = mask(src, shape, crop=True)
                            out_meta = src.meta.copy()

                            # Update the metadata with new dimensions, transform, and CRS
                            out_meta.update(
                                {
                                    "driver": "GTiff",
                                    "height": out_image.shape[1],
                                    "width": out_image.shape[2],
                                    "transform": out_transform,
                                    "dtype": out_image.dtype,
                                    "compress": "lzw",  # lossless compression algorithm
                                }
                            )

                            # Save the clipped raster to a new file
                            with rasterio.open(
                                subregions_file, "w", **out_meta
                            ) as dest:
                                dest.write(out_image)
                                print("Saved a new tif:\n", subregions_file)
                        except Exception as e:
                            # print(e)
                            print(
                                "Something went wrong while trying to cut a raster for\n",
                                region_name,
                                e,
                            )
                            return

            return subregions_file

    def get_total_sum_pixel_values(self, band=0):
        bands = []
        with rasterio.open(self.file) as dataset:
            nb_bands = dataset.count
            # Step 2: Extract the raster data
            for _ in range(nb_bands):
                bands.append(dataset.read(band + 1))  # Read the first band

        # Flatten the array to 1D and remove any no-data values (e.g., negative or extreme values)
        for band in bands:
            flat_band = band.flatten()
            flat_band = flat_band[flat_band != dataset.nodata]

            return sum(flat_band)

    def get_total_number_pixels(self):
        with rasterio.open(self.file) as src:
            band = src.read(1).flatten()
            band_filtered = band[band != src.nodata]
            return len(band_filtered) / 100
