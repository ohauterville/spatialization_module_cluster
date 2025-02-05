import osmium
import json

data_folder = "/data/mineralogie/hautervo/data/geofabrik/"
pbf_file = data_folder + "europe-latest.osm.pbf" 

class BuildingHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.buildings = []

    def way(self, w):
        # Check if the way has a "building" tag
        if 'building' in w.tags:
            # Collect the way if it has valid geometry
            try:
                coords = [(node.lon, node.lat) for node in w.nodes]
                self.buildings.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    },
                    "properties": {
                        "id": w.id,
                        "tags": dict(w.tags)
                    }
                })
            except osmium.InvalidLocationError:
                pass  # Skip invalid geometries

# Bounding box for Paris (approximate)
bbox = [2.2241, 48.8156, 2.4699, 48.9022]

# Initialize handler and apply to the PBF file
handler = BuildingHandler()
handler.apply_file(pbf_file, locations=True)

# Filter buildings within the bounding box
filtered_buildings = [
    b for b in handler.buildings
    if bbox[0] <= b["geometry"]["coordinates"][0][0][0] <= bbox[2]
    and bbox[1] <= b["geometry"]["coordinates"][0][0][1] <= bbox[3]
]

# Save to GeoJSON
with open(data_folder + "paris_buildings.geojson", "w") as f:
    geojson = {
        "type": "FeatureCollection",
        "features": filtered_buildings
    }
    json.dump(geojson, f, indent=2)

print(f"Extracted {len(filtered_buildings)} buildings.")
