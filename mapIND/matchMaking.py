import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
import requests
import folium
import random
import time

# ==============================
# CONFIG
# ==============================
OSRM_URL = "http://127.0.0.1:5001"
MAX_CANDIDATES = 5     # nearest drivers per rider
REQUEST_DELAY = 0.01  # OSRM safety delay


# ==============================
# OSRM ROUTING
# ==============================
def osrm_route(start, end):
    """
    start, end: (lat, lon)
    returns: (route_coords, travel_time_sec)
    """
    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{start[1]},{start[0]};{end[1]},{end[0]}"
        f"?overview=full&geometries=geojson"
    )

    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        route = data["routes"][0]
        coords = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
        return coords, route["duration"]
    except:
        return None, 1e9


# ==============================
# MATCHING ENGINE
# ==============================
def match_riders_drivers(riders, drivers):
    """
    riders, drivers: list of (lat, lon)
    returns:
        matches: [(rider_idx, driver_idx)]
        routes: {(rider_idx, driver_idx): route_coords}
    """

    driver_tree = cKDTree(np.array(drivers))
    assigned_drivers = set()
    routes = {}
    matches = []

    for r_idx, rider in enumerate(riders):
        # 1️⃣ Nearest drivers (euclidean prefilter)
        dists, candidate_idxs = driver_tree.query(
            rider,
            k=min(MAX_CANDIDATES, len(drivers))
        )

        if np.isscalar(candidate_idxs):
            candidate_idxs = [candidate_idxs]

        candidate_idxs = [
            d for d in candidate_idxs if d not in assigned_drivers
        ]

        if not candidate_idxs:
            continue

        # 2️⃣ OSRM travel-time cost
        costs = []
        for d_idx in candidate_idxs:
            route, duration = osrm_route(drivers[d_idx], riders[r_idx])
            routes[(r_idx, d_idx)] = route
            costs.append(duration)
            time.sleep(REQUEST_DELAY)

        # 3️⃣ Assign closest driver
        best = candidate_idxs[int(np.argmin(costs))]
        matches.append((r_idx, best))
        assigned_drivers.add(best)

    return matches, routes


# ==============================
# MAP VISUALIZATION
# ==============================
def plot_map(riders, drivers, matches, routes, filename="pickup_routes.html"):
    m = folium.Map(location=riders[0], zoom_start=14)

    # Riders
    for i, (lat, lon) in enumerate(riders):
        folium.Marker(
            [lat, lon],
            popup=f"Rider {i}",
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

    # Drivers
    for i, (lat, lon) in enumerate(drivers):
        folium.Marker(
            [lat, lon],
            popup=f"Driver {i}",
            icon=folium.Icon(color="green", icon="car")
        ).add_to(m)

    # Routes
    for r_idx, d_idx in matches:
        route = routes.get((r_idx, d_idx))
        if route:
            folium.PolyLine(
                route,
                color=random.choice(["red", "orange", "purple"]),
                weight=5,
                opacity=0.9,
                tooltip=f"Driver {d_idx} → Rider {r_idx}"
            ).add_to(m)

    m.save(filename)
    print(f"✅ Map saved as {filename}")


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":

    # 🚏 Sample Noida locations
    rider_locations = [(28.6178222358956, 77.36453560612044),(28.624484197874366, 77.36490479041693)]

    driver_locations = [(28.62803100034599, 77.35535172266178),(28.627964596604063, 77.37408216920637)]

    print("🚀 Running Uber-style matching...")
    matches, routes = match_riders_drivers(rider_locations, driver_locations)

    for r, d in matches:
        print(f"Rider {r} matched with Driver {d}")

    plot_map(rider_locations, driver_locations, matches, routes)
