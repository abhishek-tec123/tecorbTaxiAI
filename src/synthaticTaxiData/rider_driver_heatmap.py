from folium.plugins import HeatMap
from shapely.geometry import Polygon
from h3 import h3
from nyc_polygon import NYC_POLYGON
import folium

from helperForHeatMap import fetch_points, prepare_points, create_map

# ============================================================
# 1. Config
# ============================================================
START_TS = "2025-07-07 07:00:00"
END_TS   = "2025-07-07 08:00:00"
TIME_LABEL = f"{START_TS} → {END_TS}"

DEMAND_GRADIENT = {0.0: "#FADBD8", 0.6: "#E74C3C", 1.0: "#C0392B"}
SUPPLY_GRADIENT = {0.0: "#D6EAF8", 0.6: "#3498DB", 1.0: "#1F618D"}
NET_GRADIENT = {0.0: "#D6EAF8", 0.5: "#FFFFFF", 1.0: "#FADBD8"}

# ============================================================
# Utility: Net → Color
# ============================================================
def net_to_color(net, max_abs):
    if net == 0 or max_abs == 0:
        return "#FFFFFF"
    intensity = min(abs(net) / max_abs, 1.0)
    if net > 0:
        r, g, b = 250, int(219 - 120 * intensity), int(216 - 120 * intensity)
    else:
        r, g, b = int(214 - 120 * intensity), int(234 - 120 * intensity), 248
    return f"#{r:02x}{g:02x}{b:02x}"

# ============================================================
# 5. Heatmap layers
# ============================================================
def add_heatmaps(layer_riders, layer_drivers, layer_net, rider_points, driver_points):
    HeatMap(rider_points, radius=45, blur=75, min_opacity=0.1, gradient=DEMAND_GRADIENT, max_zoom=1).add_to(layer_riders)
    HeatMap(driver_points, radius=40, blur=75, min_opacity=0.1, gradient=SUPPLY_GRADIENT, max_zoom=1).add_to(layer_drivers)
    net_points = [[lat, lon, 1] for lat, lon, _ in rider_points] + [[lat, lon, -1] for lat, lon, _ in driver_points]
    HeatMap(net_points, radius=40, blur=75, min_opacity=0.1, gradient=NET_GRADIENT, max_zoom=1).add_to(layer_net)

# ============================================================
# 6. Hex overlay + collect stats
# ============================================================
def add_hex_overlay(layer_net, rider_hex, driver_hex):
    all_hexes = set(rider_hex) | set(driver_hex)
    net_values = [(rider_hex[h] - driver_hex[h]) for h in all_hexes]
    max_abs = max(abs(v) for v in net_values) if net_values else 0

    hex_stats = []
    for h in all_hexes:
        r = rider_hex[h]
        d = driver_hex[h]
        net = r - d

        boundary = h3.h3_to_geo_boundary(h, geo_json=True)
        poly = Polygon([(lon, lat) for lon, lat in boundary])
        clipped = NYC_POLYGON.intersection(poly)
        if clipped.is_empty:
            continue

        folium.Polygon(
            locations=[(lat, lon) for lon, lat in clipped.exterior.coords],
            fill=True,
            fill_color=net_to_color(net, max_abs),
            fill_opacity=0.10,
            color="#B0B0B0",
            weight=0.1,
            popup=f"<b>Hex:</b> {h}<br><b>Riders:</b> {r}<br><b>Drivers:</b> {d}<br><b>Net:</b> {net}<br><b>Time:</b> {TIME_LABEL}"
        ).add_to(layer_net)

        hex_stats.append({"hex": h, "riders": r, "drivers": d, "net": net})

    return hex_stats

# ============================================================
# 7. Main
# ============================================================
def map_result_dynamic(start_ts, end_ts):
    rider_rows = fetch_points("riders", start_ts, end_ts)
    driver_rows = fetch_points("drivers", start_ts, end_ts)

    rider_points, rider_hex = prepare_points(rider_rows)
    driver_points, driver_hex = prepare_points(driver_rows)

    m = create_map(rider_points + driver_points)

    layer_riders = folium.FeatureGroup("Rider Demand", show=True)
    layer_drivers = folium.FeatureGroup("Driver Supply", show=False)
    layer_net = folium.FeatureGroup("Net Demand", show=False)

    add_heatmaps(layer_riders, layer_drivers, layer_net, rider_points, driver_points)
    hex_stats = add_hex_overlay(layer_net, rider_hex, driver_hex)

    for layer in [layer_riders, layer_drivers, layer_net]:
        m.add_child(layer)

    folium.LayerControl(collapsed=False).add_to(m)

    map_filename = "rider_driver_heatmap.html"
    m.save(map_filename)
    print(f"✅ Saved → {map_filename}")

    return {"map_file": map_filename, "hex_stats": hex_stats}


# ============================================================

# result = map_result()
# print("✅ Hex stats sample:", result["hex_stats"][:5])
