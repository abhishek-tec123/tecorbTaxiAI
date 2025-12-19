# ============================================================
# Rider–Driver Static Heatmap Analytics (SEPARATE MAP)
# ============================================================

import mysql.connector
import folium
from folium.plugins import HeatMap
from h3 import h3
from shapely.geometry import Polygon, Point
from collections import defaultdict
from nyc_polygon import NYC_POLYGON

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
    database="taxiProduction",
)
cursor = conn.cursor(dictionary=True)

cursor.execute("""
    SELECT lat, lon
    FROM riders
    WHERE activity_at BETWEEN %s AND %s
""", (START_TS, END_TS))
rider_rows = cursor.fetchall()

cursor.execute("""
    SELECT lat, lon
    FROM drivers
    WHERE activity_at BETWEEN %s AND %s
""", (START_TS, END_TS))
driver_rows = cursor.fetchall()

cursor.close()
conn.close()

# -----------------------------
# 3. H3 resolution
# -----------------------------
resolution = 7

# -----------------------------
# 4. Hex counts
# -----------------------------
rider_hex = defaultdict(int)
driver_hex = defaultdict(int)

for r in rider_rows:
    pt = Point(r["lon"], r["lat"])
    if NYC_POLYGON.contains(pt):
        h = h3.geo_to_h3(r["lat"], r["lon"], resolution)
        rider_hex[h] += 1

for d in driver_rows:
    pt = Point(d["lon"], d["lat"])
    if NYC_POLYGON.contains(pt):
        h = h3.geo_to_h3(d["lat"], d["lon"], resolution)
        driver_hex[h] += 1

all_hexes = set(rider_hex) | set(driver_hex)

# -----------------------------
# 5. Map center
# -----------------------------
def center_hexes(hexes):
    lats, lons = zip(*(h3.h3_to_geo(h) for h in hexes))
    return sum(lats)/len(lats), sum(lons)/len(lons)

center_lat, center_lon = center_hexes(all_hexes)

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="CartoDB Positron"
)

# -----------------------------
# 6. Feature groups
# -----------------------------
layer_rider_heat  = folium.FeatureGroup(name="🔥 Rider Hex Heat", show=True)
layer_driver_heat = folium.FeatureGroup(name="🔥 Driver Hex Heat", show=False)
layer_imbalance   = folium.FeatureGroup(name="⚖️ Rider/Driver Imbalance", show=True)

# -----------------------------
# 7. Hex-weighted heatmaps
# -----------------------------
rider_heat_data = []
driver_heat_data = []

for h in all_hexes:
    lat, lon = h3.h3_to_geo(h)
    if rider_hex[h] > 0:
        rider_heat_data.append([lat, lon, rider_hex[h]])
    if driver_hex[h] > 0:
        driver_heat_data.append([lat, lon, driver_hex[h]])

HeatMap(
    rider_heat_data,
    radius=25,
    blur=30,
    min_opacity=0.0
).add_to(layer_rider_heat)

HeatMap(
    driver_heat_data,
    radius=25,
    blur=30,
    min_opacity=0.0
).add_to(layer_driver_heat)

# -----------------------------
# 8. Imbalance coloring
# -----------------------------
def imbalance_color(r, d):
    if r == 0 and d == 0:
        return "#eeeeee"

    ratio = (r - d) / max(r + d, 1)

    if ratio > 0.5:
        return "#800026"   # rider-heavy
    elif ratio > 0.2:
        return "#FC4E2A"
    elif ratio > -0.2:
        return "#FED976"   # balanced
    elif ratio > -0.5:
        return "#74C476"
    else:
        return "#006837"   # driver-heavy

for h in all_hexes:
    r = rider_hex[h]
    d = driver_hex[h]

    if r == 0 and d == 0:
        continue

    boundary = h3.h3_to_geo_boundary(h, geo_json=True)
    poly = Polygon([(lon, lat) for lon, lat in boundary])
    clipped = NYC_POLYGON.intersection(poly)

    if clipped.is_empty:
        continue

    folium.Polygon(
        locations=[(lat, lon) for lon, lat in clipped.exterior.coords],
        fill=True,
        fill_color=imbalance_color(r, d),
        fill_opacity=0.0,
        color="black",
        weight=0.1,
        popup=f"""
        <b>Hex:</b> {h}<br>
        <b>Riders:</b> {r}<br>
        <b>Drivers:</b> {d}<br>
        <b>Imbalance:</b> {r - d}
        """
    ).add_to(layer_imbalance)

# -----------------------------
# 9. Add layers & save
# -----------------------------
m.add_child(layer_rider_heat)
m.add_child(layer_driver_heat)
m.add_child(layer_imbalance)

folium.LayerControl(collapsed=False).add_to(m)

m.save("rider_driver_heatmap.html")
print("✅ Static map saved → rider_driver_heatmap.html")
