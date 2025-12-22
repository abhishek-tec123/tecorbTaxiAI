# # ============================================================
# # Rider–Driver Net Demand Continuous Heatmap (NO HEX VISUALS)
# # ============================================================

# import mysql.connector
# import folium
# from folium.plugins import HeatMap
# from shapely.geometry import Point
# from nyc_polygon import NYC_POLYGON

# # -----------------------------
# # 1. Time window
# # -----------------------------
# START_TS = "2025-07-07 07:00:00"
# END_TS   = "2025-07-07 08:00:00"

# # -----------------------------
# # 2. MySQL connection
# # -----------------------------
# conn = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="root@123",
#     database="taxiProduction",
# )
# cursor = conn.cursor(dictionary=True)

# cursor.execute("""
#     SELECT lat, lon
#     FROM riders
#     WHERE activity_at BETWEEN %s AND %s
# """, (START_TS, END_TS))
# rider_rows = cursor.fetchall()

# cursor.execute("""
#     SELECT lat, lon
#     FROM drivers
#     WHERE activity_at BETWEEN %s AND %s
# """, (START_TS, END_TS))
# driver_rows = cursor.fetchall()

# cursor.close()
# conn.close()

# # -----------------------------
# # 3. Filter points inside NYC
# # -----------------------------
# rider_points = [
#     [r["lat"], r["lon"], 1]
#     for r in rider_rows
#     if NYC_POLYGON.contains(Point(r["lon"], r["lat"]))
# ]

# driver_points = [
#     [d["lat"], d["lon"], 1]
#     for d in driver_rows
#     if NYC_POLYGON.contains(Point(d["lon"], d["lat"]))
# ]

# # -----------------------------
# # 4. Map center
# # -----------------------------
# all_points = rider_points + driver_points
# center_lat = sum(p[0] for p in all_points) / len(all_points)
# center_lon = sum(p[1] for p in all_points) / len(all_points)

# FIXED_ZOOM = 12

# m = folium.Map(
#     location=[center_lat, center_lon],
#     zoom_start=FIXED_ZOOM,
#     min_zoom=FIXED_ZOOM,
#     max_zoom=FIXED_ZOOM,
#     tiles="CartoDB Positron",
#     control_scale=True
# )


# # -----------------------------
# # 5. Feature groups
# # -----------------------------
# layer_riders   = folium.FeatureGroup(name="🔥 Rider Demand", show=True)
# layer_drivers  = folium.FeatureGroup(name="🚗 Driver Supply", show=False)
# layer_net      = folium.FeatureGroup(name="⚖️ Net Demand (Riders − Drivers)", show=True)

# # -----------------------------
# # 6. Gradients
# # -----------------------------
# DEMAND_GRADIENT = {
#     0.0: "#2ECC71",  # green
#     0.4: "#F1C40F",  # yellow
#     0.7: "#E67E22",  # orange
#     1.0: "#C0392B",  # red
# }

# SUPPLY_GRADIENT = {
#     0.0: "#C0392B",  # red (low supply)
#     0.4: "#F1C40F",
#     0.7: "#2ECC71",  # green (high supply)
#     1.0: "#1E8449",
# }

# NET_GRADIENT = {
#     0.0: "#006837",  # strong driver surplus
#     0.4: "#7FBF7B",  # mild surplus
#     0.5: "#FFFFBF",  # balanced
#     0.7: "#FC8D59",  # mild rider surplus
#     1.0: "#800026",  # strong rider surplus
# }

# HEAT_ZOOM_LOCK = 1

# # -----------------------------
# # 7. Rider heatmap
# # -----------------------------
# HeatMap(
#     rider_points,
#     radius=45,
#     blur=55,
#     min_opacity=0.25,
#     gradient=DEMAND_GRADIENT,
#     max_zoom=HEAT_ZOOM_LOCK
# ).add_to(layer_riders)

# # -----------------------------
# # 8. Driver heatmap
# # -----------------------------
# HeatMap(
#     driver_points,
#     radius=45,
#     blur=55,
#     min_opacity=0.25,
#     gradient=SUPPLY_GRADIENT,
#     max_zoom=HEAT_ZOOM_LOCK
# ).add_to(layer_drivers)

# # -----------------------------
# # 9. NET DEMAND SURFACE
# # -----------------------------
# # Riders add +1, drivers add -1
# net_points = []

# for lat, lon, _ in rider_points:
#     net_points.append([lat, lon, 1])

# for lat, lon, _ in driver_points:
#     net_points.append([lat, lon, -1])

# HeatMap(
#     net_points,
#     radius=50,
#     blur=65,
#     min_opacity=0.3,
#     gradient=NET_GRADIENT,
#     max_zoom=HEAT_ZOOM_LOCK
# ).add_to(layer_net)

# # -----------------------------
# # 10. Add layers & controls
# # -----------------------------
# m.add_child(layer_riders)
# m.add_child(layer_drivers)
# m.add_child(layer_net)

# folium.LayerControl(collapsed=False).add_to(m)

# # -----------------------------
# # 11. Save
# # -----------------------------
# m.save("rider_driver_heatmap.html")
# print("✅ Saved → rider_driver_heatmap.html")



# ============================================================
# Rider–Driver Net Demand with Optional Interactive Hex Overlay
# ============================================================

import mysql.connector
import folium
from folium.plugins import HeatMap
from shapely.geometry import Point, Polygon
from collections import defaultdict
from h3 import h3
from nyc_polygon import NYC_POLYGON

# -----------------------------
# 1. Time window
# -----------------------------
START_TS = "2025-07-07 07:00:00"
END_TS   = "2025-07-07 08:00:00"
TIME_LABEL = f"{START_TS} → {END_TS}"

# -----------------------------
# 2. H3 resolution (for overlay only)
# -----------------------------
H3_RESOLUTION = 7

# -----------------------------
# 3. MySQL connection
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
# 4. Filter + prepare points
# -----------------------------
rider_points = []
driver_points = []

rider_hex = defaultdict(int)
driver_hex = defaultdict(int)

for r in rider_rows:
    pt = Point(r["lon"], r["lat"])
    if NYC_POLYGON.contains(pt):
        rider_points.append([r["lat"], r["lon"], 1])
        h = h3.geo_to_h3(r["lat"], r["lon"], H3_RESOLUTION)
        rider_hex[h] += 1

for d in driver_rows:
    pt = Point(d["lon"], d["lat"])
    if NYC_POLYGON.contains(pt):
        driver_points.append([d["lat"], d["lon"], 1])
        h = h3.geo_to_h3(d["lat"], d["lon"], H3_RESOLUTION)
        driver_hex[h] += 1

all_hexes = set(rider_hex) | set(driver_hex)

# -----------------------------
# 5. Map center
# -----------------------------
all_points = rider_points + driver_points
center_lat = sum(p[0] for p in all_points) / len(all_points)
center_lon = sum(p[1] for p in all_points) / len(all_points)

FIXED_ZOOM = 13

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=FIXED_ZOOM,
    min_zoom=FIXED_ZOOM,
    max_zoom=FIXED_ZOOM,
    tiles="CartoDB Positron"
)

m.scrollWheelZoom = False
m.doubleClickZoom = False

# -----------------------------
# 6. Feature groups
# -----------------------------
layer_riders = folium.FeatureGroup(name="🔥 Rider Demand", show=True)
layer_drivers = folium.FeatureGroup(name="🚗 Driver Supply", show=False)
layer_net = folium.FeatureGroup(name="⚖️ Net Demand", show=False)
layer_hex = folium.FeatureGroup(name="⬡ Hex Overlay (Interactive)", show=False)

# -----------------------------
# 7. Gradients
# -----------------------------
DEMAND_GRADIENT = {
    0.0: "#2ECC71",
    0.4: "#F1C40F",
    0.7: "#E67E22",
    1.0: "#C0392B",
}

SUPPLY_GRADIENT = {
    0.0: "#C0392B",
    0.5: "#F1C40F",
    1.0: "#1E8449",
}

NET_GRADIENT = {
    0.0: "#006837",
    0.5: "#FFFFBF",
    1.0: "#800026",
}

# -----------------------------
# 8. Heatmaps (zoom-stable)
# -----------------------------
HEAT_ZOOM_LOCK = 1

HeatMap(
    rider_points,
    radius=45,
    blur=55,
    min_opacity=0.1,
    gradient=DEMAND_GRADIENT,
    max_zoom=HEAT_ZOOM_LOCK
).add_to(layer_riders)

HeatMap(
    driver_points,
    radius=45,
    blur=55,
    min_opacity=0.1,
    gradient=SUPPLY_GRADIENT,
    max_zoom=HEAT_ZOOM_LOCK
).add_to(layer_drivers)

# Net = riders +1, drivers -1
net_points = (
    [[lat, lon, 1] for lat, lon, _ in rider_points] +
    [[lat, lon, -1] for lat, lon, _ in driver_points]
)

HeatMap(
    net_points,
    radius=50,
    blur=65,
    min_opacity=0.1,
    gradient=NET_GRADIENT,
    max_zoom=HEAT_ZOOM_LOCK
).add_to(layer_net)

# -----------------------------
# 9. HEX OVERLAY (LIGHT + CLICKABLE)
# -----------------------------
def light_hex_color(r, d):
    if r > d:
        return "#FC8D59"  # light red
    elif d > r:
        return "#91CF60"  # light green
    else:
        return "#E0E0E0"  # neutral

for h in all_hexes:
    r = rider_hex[h]
    d = driver_hex[h]

    boundary = h3.h3_to_geo_boundary(h, geo_json=True)
    poly = Polygon([(lon, lat) for lon, lat in boundary])
    clipped = NYC_POLYGON.intersection(poly)

    if clipped.is_empty:
        continue

    folium.Polygon(
        locations=[(lat, lon) for lon, lat in clipped.exterior.coords],
        fill=True,
        fill_color=light_hex_color(r, d),
        fill_opacity=0.18,     # VERY LIGHT
        color="#555555",
        weight=0.4,
        popup=folium.Popup(
            f"""
            <b>Hex ID:</b> {h}<br>
            <b>Riders:</b> {r}<br>
            <b>Drivers:</b> {d}<br>
            <b>Net:</b> {r - d}<br>
            <b>Time:</b> {TIME_LABEL}
            """,
            max_width=300
        )
    ).add_to(layer_hex)

# -----------------------------
# 10. Add layers & control
# -----------------------------
m.add_child(layer_riders)
m.add_child(layer_drivers)
m.add_child(layer_net)
m.add_child(layer_hex)

folium.LayerControl(collapsed=False).add_to(m)

# -----------------------------
# 11. Save
# -----------------------------
m.save("rider_driver_heatmap.html")
print("✅ Saved → rider_driver_heatmap.html")
