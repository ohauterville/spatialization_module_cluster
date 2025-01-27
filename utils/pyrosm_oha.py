from pyrosm import get_data, OSM
import os

region_name = "nord_pas_de_calais"
dir_name = "/data/mineralogie/hautervo/data/pyrosm"

print("Getting data for ", region_name)
print("The file will be saved in ", dir_name)
pbf = get_data(region_name, directory=dir_name)

osm = OSM(pbf)

columns_to_keep = ["building", "geometry", "amenity", "building:use", 
                   "landuse", "building:levels", "building:material"]

print("Getting buildings...")
buildings = osm.get_buildings()

b = buildings[buildings.geom_type == "Polygon"]
b = b[columns_to_keep]

print(b.shape, b.head())

print("Saving shp...")
output_file = os.path.join(dir_name,"shp", region_name, region_name)+".shp"
os.makedirs(os.path.dirname(output_file), exist_ok="True")
b.to_file(output_file)

print("Done.")