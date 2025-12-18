import asyncio
import aiohttp
import random
import math
import folium
import numpy as np
from scipy.optimize import linear_sum_assignment

# =========================
# CONFIG
# =========================

OSRM_URL = "http://127.0.0.1:5002"   # NYC OSRM
MAX_RADIUS_KM = 3
NUM_RANDOM_DRIVERS = 3
NUM_RIDERS = 3

# =========================
# GEO UTIL
# =========================

def random_point_within_radius(lat, lon, radius_km):
    radius_deg = radius_km / 111
    u, v = random.random(), random.random()
    w = radius_deg * math.sqrt(u)
    t = 2 * math.pi * v
    return lat + w * math.cos(t), lon + w * math.sin(t)

# =========================
# OSRM
# =========================

async def osrm_route(session, start, end):
    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{start[1]},{start[0]};{end[1]},{end[0]}"
        "?overview=full&geometries=geojson"
    )
    async with session.get(url) as r:
        data = await r.json()
        route = data["routes"][0]
        return route["duration"], route["geometry"]["coordinates"]

# =========================
# MAIN
# =========================

async def main():

    # -------------------------
    # Static Drivers (fixed)
    # -------------------------
    drivers = [
        {"id": "S0", "lat": 40.748817, "lon": -73.985428},  # Midtown
        {"id": "S1", "lat": 40.730610, "lon": -73.935242},  # Queens
        {"id": "S2", "lat": 40.742054, "lon": -73.991202},  # Chelsea
    ]

    # -------------------------
    # Random Drivers
    # -------------------------
    for i in range(NUM_RANDOM_DRIVERS):
        lat, lon = random_point_within_radius(40.74, -73.98, MAX_RADIUS_KM)
        drivers.append({"id": f"R{i}", "lat": lat, "lon": lon})

    # -------------------------
    # Riders
    # -------------------------
    riders = []
    for i in range(NUM_RIDERS):
        lat, lon = random_point_within_radius(40.74, -73.98, 2)
        riders.append({"id": i, "lat": lat, "lon": lon})

    print("\n🚗 Drivers")
    for d in drivers:
        print(d)

    print("\n🧍 Riders")
    for r in riders:
        print(r)

    # -------------------------
    # COST MATRIX
    # -------------------------
    cost = np.full((len(riders), len(drivers)), 1e9)

    async with aiohttp.ClientSession() as session:
        for i, r in enumerate(riders):
            for j, d in enumerate(drivers):
                try:
                    duration, _ = await osrm_route(
                        session,
                        (d["lat"], d["lon"]),
                        (r["lat"], r["lon"])
                    )
                    cost[i, j] = duration
                except:
                    pass

    # -------------------------
    # HUNGARIAN MATCHING
    # -------------------------
    row_idx, col_idx = linear_sum_assignment(cost)

    matches = []
    for r_i, d_i in zip(row_idx, col_idx):
        if cost[r_i, d_i] < 1e8:
            matches.append((riders[r_i], drivers[d_i], cost[r_i, d_i]))

    # -------------------------
    # MAP
    # -------------------------
    m = folium.Map(location=[40.74, -73.98], zoom_start=12)

    async with aiohttp.ClientSession() as session:
        for r, d, t in matches:
            _, coords = await osrm_route(
                session,
                (d["lat"], d["lon"]),
                (r["lat"], r["lon"])
            )

            folium.Marker(
                [r["lat"], r["lon"]],
                popup=f"Rider {r['id']}",
                icon=folium.Icon(color="red", icon="user")
            ).add_to(m)

            folium.Marker(
                [d["lat"], d["lon"]],
                popup=f"Driver {d['id']} ({t/60:.1f} min)",
                icon=folium.Icon(color="green", icon="car")
            ).add_to(m)

            folium.PolyLine(
                [(lat, lon) for lon, lat in coords],
                weight=5
            ).add_to(m)

    m.save("map.html")

    # -------------------------
    # RESULT
    # -------------------------
    print("\n✅ MATCH RESULTS")
    for r, d, t in matches:
        print(f"Driver {d['id']} → Rider {r['id']} | {t/60:.2f} min")

    print("\n🗺 map.html generated")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    asyncio.run(main())
