"""
nyc_polygon_full.py
Full script: fill polygon with H3 hexes, clip boundary hexes to polygon,
draw results in folium, and print hex summary (IDs, count, area).
"""

import csv
import os
import folium
import h3
from shapely.geometry import Polygon
from shapely.ops import unary_union

# -----------------------------------------
# 1. Polygon coordinates (lat, lon) — user provided
# -----------------------------------------
POLY_COORDS = [
    (40.915022365265344, -73.9095218048947),
    (40.83239340697381, -73.95173116777548),
    (40.75250363837537, -74.0084793112041),
    (40.699190397557544, -74.01832816254294),
    (40.709145444438995, -73.97799477134575),
    (40.79938395758287, -73.92781252880971),
    (40.81119786011659, -73.79653638839851),
    (40.89765402355925, -73.82088214284505),
    (40.915022365265344, -73.9095218048947),  # ensure closed
]

# -----------------------------------------
# 2. Prepare polygon shapes and geojson coords
# -----------------------------------------
# shapely expects (x, y) = (lon, lat)
NYC_POLYGON = Polygon([(lon, lat) for lat, lon in POLY_COORDS])
MIN_LAT = min([lat for lat, lon in POLY_COORDS])
MAX_LAT = max([lat for lat, lon in POLY_COORDS])
MIN_LON = min([lon for lat, lon in POLY_COORDS])
MAX_LON = max([lon for lat, lon in POLY_COORDS])

# for h3.polyfill_geojson we need coordinates as [lon, lat]
GEOJSON_COORDS = [(lon, lat) for (lat, lon) in POLY_COORDS]
geojson_polygon = {"type": "Polygon", "coordinates": [GEOJSON_COORDS]}

# -----------------------------------------
# 3. H3 resolution and polyfill
# -----------------------------------------
RESOLUTION = 7  # change if you want smaller/larger hexes (0..15)

# polyfill returns hexes whose centers are inside the polygon
inside_hexes = set(h3.polyfill_geojson(geojson_polygon, RESOLUTION))
print(f"Polyfill (center-inside) hex count: {len(inside_hexes)}")

# expand neighborhood to ensure no gaps at edges.
# radius 2 is usually enough; increase if you still see tiny gaps
NEIGHBOR_RADIUS = 2

candidate_hexes = set(inside_hexes)
for h in list(inside_hexes):
    candidate_hexes |= set(h3.k_ring(h, NEIGHBOR_RADIUS))

print(f"Candidate hex pool size (after k_ring): {len(candidate_hexes)}")

# -----------------------------------------
# 4. Keep only hexes that intersect the polygon (and compute clipped shapes)
# -----------------------------------------
intersected_hexes = []          # list of hex ids that intersect
intersections = {}              # hex_id -> shapely intersection polygon

for hex_id in candidate_hexes:
    # h3.h3_to_geo_boundary returns list of (lat, lon)
    hex_boundary_latlon = h3.h3_to_geo_boundary(hex_id)
    # build shapely hex polygon (lon, lat)
    hex_poly = Polygon([(lon, lat) for lat, lon in hex_boundary_latlon])

    if hex_poly.intersects(NYC_POLYGON):
        inter = hex_poly.intersection(NYC_POLYGON)
        # filter tiny intersections (optional) - keep all that have area > 0
        if inter.is_empty:
            continue
        # store
        intersected_hexes.append(hex_id)
        intersections[hex_id] = inter

print(f"Intersected hex count: {len(intersected_hexes)}")

# -----------------------------------------
# 5. Compute hex area (robust to h3 version differences)
#    Try unit-aware API first, fall back to old API (returns km^2)
# -----------------------------------------
hex_area_km2 = None
try:
    # newer h3-py versions support unit argument, try 'km2'
    hex_area_km2 = h3.hex_area(resolution=RESOLUTION, unit="km2")
except Exception:
    try:
        # sometimes signature is hex_area(resolution, unit)
        hex_area_km2 = h3.hex_area(RESOLUTION, "km2")
    except Exception:
        # old versions may only accept a single arg and return km^2
        hex_area_km2 = h3.hex_area(RESOLUTION)

hex_area_m2 = hex_area_km2 * 1_000_000.0

# -----------------------------------------
# 6. Build folium map and draw results
# -----------------------------------------
center_lat = sum([p[0] for p in POLY_COORDS]) / len(POLY_COORDS)
center_lon = sum([p[1] for p in POLY_COORDS]) / len(POLY_COORDS)
m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# draw original polygon (outline)
folium.Polygon(
    locations=POLY_COORDS,
    color="red",
    weight=3,
    fill=False,
    popup="Original polygon",
).add_to(m)

# draw all clipped intersection polygons (blue fill)
for hex_id, inter in intersections.items():
    # intersection can be Polygon or MultiPolygon
    if inter.geom_type == "Polygon":
        coords = [(lat, lon) for lon, lat in inter.exterior.coords]
        folium.Polygon(locations=coords, color="blue", weight=1, fill=True, fill_opacity=0.4).add_to(m)
    elif inter.geom_type == "MultiPolygon":
        for part in inter:
            coords = [(lat, lon) for lon, lat in part.exterior.coords]
            folium.Polygon(locations=coords, color="blue", weight=1, fill=True, fill_opacity=0.4).add_to(m)

# # (Optional) draw hex centers as small black dots
# for hex_id in intersected_hexes:
#     c_lat, c_lon = h3.h3_to_geo(hex_id)
#     folium.CircleMarker(location=[c_lat, c_lon], radius=2, color="black", fill=True).add_to(m)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_DIR = os.path.join(BASE_DIR, "map_file")
os.makedirs(MAP_DIR, exist_ok=True)

# Save map into map_file directory
OUT_HTML = os.path.join(MAP_DIR, "nycMap_polygon_intersection_h3.html")
m.save(OUT_HTML)
print(f"Map saved as {OUT_HTML}")

# -----------------------------------------
# 7. Print summary and list hex IDs
# -----------------------------------------
print("\n========== HEX SUMMARY ==========")
print(f"Resolution: {RESOLUTION}")
print(f"Per-hex area (km²): {hex_area_km2:.6f}")
print(f"Per-hex area (m²): {hex_area_m2:,.2f}")
print(f"Total intersected hexagons: {len(intersected_hexes)}")
print("=================================\n")

# Print all hex IDs (one per line)
for h in intersected_hexes[:5]:
    print(h)

# -----------------------------------------
# 8. (Optional) Save hex list to CSV for later use, in map_file directory
# -----------------------------------------
CSV_OUT = os.path.join(MAP_DIR, "intersected_hexes.csv")
with open(CSV_OUT, "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["hex_id", "resolution", "hex_area_km2", "hex_area_m2"])
    for h in intersected_hexes:
        writer.writerow([h, RESOLUTION, f"{hex_area_km2:.6f}", f"{hex_area_m2:.2f}"])

print(f"\nHex list exported to: {CSV_OUT}")
