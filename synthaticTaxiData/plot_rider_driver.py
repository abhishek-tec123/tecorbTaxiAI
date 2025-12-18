# # rider driver both in the same hex with map-----------------------------------------------------------------

import mysql.connector
import folium
from h3 import h3
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from nyc_polygon import NYC_POLYGON, POLY_COORDS
from schema import HEX_LIST  # optional

# -----------------------------
# 1. Time window
# -----------------------------
START_TS = "2025-07-07 07:00:00"
END_TS   = "2025-07-07 08:00:00"

# -----------------------------
# 2. MySQL connection
# -----------------------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root@123",
    database="taxi",
)
cursor = conn.cursor()

# -----------------------------
# 3. Fetch riders & drivers in time window
# -----------------------------
cursor.execute("SELECT lat, lon FROM riders WHERE activity_at BETWEEN %s AND %s", (START_TS, END_TS))
rider_rows = cursor.fetchall()

cursor.execute("SELECT lat, lon FROM drivers WHERE activity_at BETWEEN %s AND %s", (START_TS, END_TS))
driver_rows = cursor.fetchall()

cursor.close()
conn.close()

# -----------------------------
# 4. H3 resolution
# -----------------------------
resolution = 7
parent_resolution = 6

# -----------------------------
# 5. Convert points to hexes (inside polygon only)
# -----------------------------
rider_hex_counts = {}
driver_hex_counts = {}

for lat, lon in rider_rows:
    pt = Point(lon, lat)
    if NYC_POLYGON.contains(pt):
        h = h3.geo_to_h3(lat, lon, resolution)
        rider_hex_counts[h] = rider_hex_counts.get(h, 0) + 1

for lat, lon in driver_rows:
    pt = Point(lon, lat)
    if NYC_POLYGON.contains(pt):
        h = h3.geo_to_h3(lat, lon, resolution)
        driver_hex_counts[h] = driver_hex_counts.get(h, 0) + 1

# -----------------------------
# 6. Build all H3 hexes that intersect polygon
# -----------------------------
geojson_polygon = {"type": "Polygon", "coordinates": [[(lon, lat) for lat, lon in POLY_COORDS]]}
candidate_hexes = h3.polyfill_geojson(geojson_polygon, resolution)

intersected_hexes = []
for h in candidate_hexes:
    hex_boundary = h3.h3_to_geo_boundary(h, geo_json=True)
    hex_poly = Polygon([(lon, lat) for lon, lat in hex_boundary])
    if NYC_POLYGON.intersects(hex_poly):
        intersected_hexes.append(h)

all_hexes = list(set(intersected_hexes) |
                 set(rider_hex_counts.keys()) |
                 set(driver_hex_counts.keys()))

# -----------------------------
# 7. Map center
# -----------------------------
def center_hexes(hex_list):
    lats, lons = [], []
    for h in hex_list:
        lat, lon = h3.h3_to_geo(h)
        lats.append(lat)
        lons.append(lon)
    return sum(lats)/len(lats), sum(lons)/len(lons)

center_lat, center_lon = center_hexes(all_hexes)
m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB Positron")

# -----------------------------
# 8. Layer groups
# -----------------------------
layer_riders_hex  = folium.FeatureGroup(name="Rider Hexes", show=True)
layer_drivers_hex = folium.FeatureGroup(name="Driver Hexes", show=True)
layer_intersected = folium.FeatureGroup(name="Intersected Hexes", show=True)
layer_rider_pts   = folium.FeatureGroup(name="Rider Points", show=True)
layer_driver_pts  = folium.FeatureGroup(name="Driver Points", show=True)
layer_polygon     = folium.FeatureGroup(name="Polygon Boundary", show=True)

# -----------------------------
# 9. Draw polygon boundary
# -----------------------------
folium.Polygon(
    locations=[(lat, lon) for lat, lon in POLY_COORDS],
    color="black",
    weight=3,
    fill=False,
    popup="NYC Polygon"
).add_to(layer_polygon)

# -----------------------------
# 10. Add rider/driver points
# -----------------------------
for lat, lon in rider_rows:
    if NYC_POLYGON.contains(Point(lon, lat)):
        folium.CircleMarker(location=[lat, lon], radius=2, color="blue",
                            fill=True, fill_opacity=0.5).add_to(layer_rider_pts)

for lat, lon in driver_rows:
    if NYC_POLYGON.contains(Point(lon, lat)):
        folium.CircleMarker(location=[lat, lon], radius=2, color="red",
                            fill=True, fill_opacity=0.5).add_to(layer_driver_pts)

# -----------------------------
# 11. Add clipped intersected hex polygons
# -----------------------------
for hex_id in all_hexes:
    hex_boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
    hex_poly = Polygon([(lon, lat) for lon, lat in hex_boundary])
    # Clip to polygon
    clipped = NYC_POLYGON.intersection(hex_poly)
    if clipped.is_empty:
        continue

    # For MultiPolygon, iterate each part
    if clipped.geom_type == 'Polygon':
        polys = [clipped]
    else:
        polys = list(clipped.geoms)

    r = rider_hex_counts.get(hex_id, 0)
    d = driver_hex_counts.get(hex_id, 0)

    for poly in polys:
        coords = [(lat, lon) for lon, lat in poly.exterior.coords]
        popup = f"<b>Hex:</b> {hex_id}<br><b>Riders:</b> {r}<br><b>Drivers:</b> {d}<br><b>Time Window:</b> {START_TS} → {END_TS}"

        # Base intersected hex
        folium.Polygon(locations=coords, color="gray", weight=1, fill=False, popup=popup).add_to(layer_intersected)

        # Riders
        if r > 0:
            folium.Polygon(locations=coords, color="blue", weight=1, fill=True, fill_opacity=0.1, popup=popup).add_to(layer_riders_hex)

        # Drivers
        if d > 0:
            folium.Polygon(locations=coords, color="red", weight=1, fill=True, fill_opacity=0.3, popup=popup).add_to(layer_drivers_hex)

# -----------------------------
# 12. Add layers + controls
# -----------------------------
m.add_child(layer_polygon)
m.add_child(layer_intersected)
m.add_child(layer_riders_hex)
m.add_child(layer_drivers_hex)
m.add_child(layer_rider_pts)
m.add_child(layer_driver_pts)
folium.LayerControl().add_to(m)

# -----------------------------
# 13. Print all hex values like (hex_id, riders, drivers)
# -----------------------------
data = []

for hex_id in all_hexes:
    r = rider_hex_counts.get(hex_id, 0)
    d = driver_hex_counts.get(hex_id, 0)
    data.append((hex_id, r, d))

# Sort by hex ID for nice output
data.sort()

print("data = [")
for h, r, d in data:
    print(f'    ("{h}", {r}, {d}),')
print("]")

m.save("map_rider_driver_polygon_hex.html")
print("Map saved → rider_driver_clipped_hex_map.html")
