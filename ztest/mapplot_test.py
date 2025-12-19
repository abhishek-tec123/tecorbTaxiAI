"""
nyc_polygon_h3_full.py

Create H3 hexagons over a polygon, clip boundary hexes,
visualize in Folium, and export results.
"""

import os
import csv
import json
import folium
import h3
import pyproj
from shapely.geometry import Polygon, mapping
from shapely.ops import transform

# --------------------------------------------------
# 1. Polygon coordinates (lat, lon)
# --------------------------------------------------
POLY_COORDS = [
    (40.85020104802893, -73.9449522610357),
    (40.83156772624141, -73.95098410503068),
    (40.75564941608272, -74.00853794981629),
    (40.70155944503239, -74.01683173530941),
    (40.711847542619694, -73.97611678834318),
    (40.74384479273579, -73.97083892484756),
    (40.78649776925977, -73.93268980026889),
    (40.84506790100021, -73.929872650689),
    (40.85020104802893, -73.9449522610357),
]

# --------------------------------------------------
# 2. Create Shapely & GeoJSON polygon
# --------------------------------------------------
shapely_polygon = Polygon([(lon, lat) for lat, lon in POLY_COORDS])

geojson_polygon = {
    "type": "Polygon",
    "coordinates": [[(lon, lat) for lat, lon in POLY_COORDS]]
}

# --------------------------------------------------
# 3. H3 settings
# --------------------------------------------------
RESOLUTION = 7          # change for larger/smaller hexes
NEIGHBOR_RADIUS = 2      # prevents boundary gaps

# --------------------------------------------------
# 4. Polyfill + expand neighbors
# --------------------------------------------------
inside_hexes = set(h3.polyfill_geojson(geojson_polygon, RESOLUTION))

candidate_hexes = set(inside_hexes)
for h in inside_hexes:
    candidate_hexes |= set(h3.k_ring(h, NEIGHBOR_RADIUS))

print(f"Center-inside hexes: {len(inside_hexes)}")
print(f"Candidate hexes: {len(candidate_hexes)}")

# --------------------------------------------------
# 5. Intersect hexes with polygon
# --------------------------------------------------
intersections = {}

for hex_id in candidate_hexes:
    boundary = h3.h3_to_geo_boundary(hex_id)
    hex_poly = Polygon([(lon, lat) for lat, lon in boundary])

    if hex_poly.intersects(shapely_polygon):
        inter = hex_poly.intersection(shapely_polygon)
        if not inter.is_empty:
            intersections[hex_id] = inter

print(f"Intersected hexes: {len(intersections)}")

# --------------------------------------------------
# 6. Area calculations (true clipped area)
# --------------------------------------------------
project = pyproj.Transformer.from_crs(
    "EPSG:4326", "EPSG:3857", always_xy=True
).transform

total_area_m2 = 0
for geom in intersections.values():
    total_area_m2 += transform(project, geom).area

# per-hex area from H3 (for reference)
try:
    hex_area_km2 = h3.hex_area(RESOLUTION, "km2")
except Exception:
    hex_area_km2 = h3.hex_area(RESOLUTION)

hex_area_m2 = hex_area_km2 * 1_000_000

# --------------------------------------------------
# 7. Folium map
# --------------------------------------------------
center_lat = sum(lat for lat, _ in POLY_COORDS) / len(POLY_COORDS)
center_lon = sum(lon for _, lon in POLY_COORDS) / len(POLY_COORDS)

m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# original polygon
folium.Polygon(
    locations=POLY_COORDS,
    color="red",
    weight=3,
    fill=False,
    popup="Original Polygon"
).add_to(m)

# clipped hexes
for geom in intersections.values():
    if geom.geom_type == "Polygon":
        coords = [(lat, lon) for lon, lat in geom.exterior.coords]
        folium.Polygon(coords, color="blue", fill=True, fill_opacity=0.4).add_to(m)
    else:
        for part in geom:
            coords = [(lat, lon) for lon, lat in part.exterior.coords]
            folium.Polygon(coords, color="blue", fill=True, fill_opacity=0.4).add_to(m)

# --------------------------------------------------
# 8. Output directory
# --------------------------------------------------
OUT_DIR = "map_file"
os.makedirs(OUT_DIR, exist_ok=True)

HTML_OUT = os.path.join(OUT_DIR, "polygon_h3_map.html")
CSV_OUT = os.path.join(OUT_DIR, "hexes.csv")
GEOJSON_OUT = os.path.join(OUT_DIR, "hexes.geojson")

m.save(HTML_OUT)

# --------------------------------------------------
# 9. Save CSV
# --------------------------------------------------
with open(CSV_OUT, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["hex_id", "resolution", "hex_area_m2"])
    for h in intersections.keys():
        writer.writerow([h, RESOLUTION, f"{hex_area_m2:.2f}"])

# --------------------------------------------------
# 10. Save GeoJSON
# --------------------------------------------------
features = []
for h, geom in intersections.items():
    features.append({
        "type": "Feature",
        "properties": {
            "hex_id": h,
            "resolution": RESOLUTION
        },
        "geometry": mapping(geom)
    })

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(GEOJSON_OUT, "w") as f:
    json.dump(geojson, f)

# --------------------------------------------------
# 11. Summary
# --------------------------------------------------
print("\n========== SUMMARY ==========")
print(f"H3 Resolution: {RESOLUTION}")
print(f"Intersected hexes: {len(intersections)}")
print(f"Single hex area (m²): {hex_area_m2:,.2f}")
print(f"True covered area (m²): {total_area_m2:,.2f}")
print(f"Map saved to: {HTML_OUT}")
print(f"CSV saved to: {CSV_OUT}")
print(f"GeoJSON saved to: {GEOJSON_OUT}")
print("=============================")
