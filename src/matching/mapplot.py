import os
import folium
from folium.plugins import MarkerCluster

CITY_CENTER = (40.74, -73.98)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_DIR = os.path.join(BASE_DIR, "map_file")


def plot_map(
    riders,
    drivers,
    matches,
    eta_lookup,
    route_lookup,
    output_file="map.html",
):
    """
    Build and save a Folium map for matched, rejected, and unmatched rides
    """

    matched_rider_ids = {m["rider_id"] for m in matches}
    matched_driver_ids = {m["driver_id"] for m in matches}

    unmatched_riders = [r for r in riders if r["id"] not in matched_rider_ids]
    unmatched_drivers = [d for d in drivers if d["id"] not in matched_driver_ids]

    matched_pairs = {(m["rider_id"], m["driver_id"]) for m in matches}
    rejected_pairs = set(route_lookup.keys()) - matched_pairs

    # -------------------------------------------------
    # MAP
    # -------------------------------------------------
    m = folium.Map(location=CITY_CENTER, zoom_start=12)

    matched_layer = folium.FeatureGroup(name="Matched Rides", show=True)
    rejected_layer = folium.FeatureGroup(name="Rejected Routes", show=False)
    unmatched_riders_layer = folium.FeatureGroup(name="Unmatched Riders", show=True)
    unmatched_drivers_layer = folium.FeatureGroup(name="Unmatched Drivers", show=True)

    unmatched_rider_cluster = MarkerCluster(name="Unmatched Rider Cluster")

    # ---------------- MATCHED RIDES ----------------
    for match in matches:
        r_id = match["rider_id"]
        d_id = match["driver_id"]

        rider = next(r for r in riders if r["id"] == r_id)
        driver = next(d for d in drivers if d["id"] == d_id)
        geom = route_lookup[(r_id, d_id)]
        stats = eta_lookup[r_id][d_id]

        folium.Marker(
            [rider["lat"], rider["lon"]],
            icon=folium.Icon(color="red", icon="user"),
            popup=f"<b>Rider {r_id}</b><br>Status: Matched"
        ).add_to(matched_layer)

        folium.Marker(
            [driver["lat"], driver["lon"]],
            icon=folium.Icon(color="green", icon="car"),
            popup=f"<b>Driver {d_id}</b><br>Status: Matched"
        ).add_to(matched_layer)

        folium.PolyLine(
            [(lat, lon) for lon, lat in geom],
            weight=5,
            color="green",
            popup=(
                f"<b>Matched Route</b><br>"
                f"ETA: {stats['eta_sec']/60:.1f} min<br>"
                f"Distance: {stats['distance_m']/1000:.2f} km"
            )
        ).add_to(matched_layer)

    # ---------------- REJECTED ROUTES ----------------
    for r_id, d_id in rejected_pairs:
        geom = route_lookup[(r_id, d_id)]
        stats = eta_lookup[r_id][d_id]

        folium.PolyLine(
            [(lat, lon) for lon, lat in geom],
            weight=2,
            opacity=0.4,
            dash_array="5,8",
            color="gray",
            popup=(
                f"<b>Rejected Route</b><br>"
                f"Rider: {r_id}<br>"
                f"Driver: {d_id}<br>"
                f"ETA: {stats['eta_sec']/60:.1f} min"
            )
        ).add_to(rejected_layer)

    # ---------------- UNMATCHED RIDERS ----------------
    for rider in unmatched_riders:
        folium.Marker(
            [rider["lat"], rider["lon"]],
            icon=folium.Icon(color="gray", icon="user"),
            popup=f"<b>Rider {rider['id']}</b><br>Status: Unmatched"
        ).add_to(unmatched_rider_cluster)

    unmatched_rider_cluster.add_to(unmatched_riders_layer)

    # ---------------- UNMATCHED DRIVERS ----------------
    for driver in unmatched_drivers:
        folium.Marker(
            [driver["lat"], driver["lon"]],
            icon=folium.Icon(color="blue", icon="car"),
            popup=f"<b>Driver {driver['id']}</b><br>Status: Unmatched"
        ).add_to(unmatched_drivers_layer)

    matched_layer.add_to(m)
    rejected_layer.add_to(m)
    unmatched_riders_layer.add_to(m)
    unmatched_drivers_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Ensure map_file directory exists and save there
    os.makedirs(MAP_DIR, exist_ok=True)
    out_path = os.path.join(MAP_DIR, output_file)
    m.save(out_path)

    return out_path
