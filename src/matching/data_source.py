import pandas as pd
import random
import math
from typing import Tuple

# =========================
# CONFIG
# =========================

RIDER_RADIUS_KM = 1.5  # max distance from each location

# =========================
# GEO UTIL
# =========================

def random_point(lat: float, lon: float, radius_km: float) -> Tuple[float, float]:
    """
    Generate a random point within radius_km around (lat, lon)
    """
    r = radius_km / 111  # approx km → degrees
    u, v = random.random(), random.random()
    w = r * math.sqrt(u)
    t = 2 * math.pi * v
    return lat + w * math.cos(t), lon + w * math.sin(t)

# =========================
# DRIVERS DATASET
# =========================

def load_drivers_df() -> pd.DataFrame:
    """
    Static driver dataset
    """
    data = [
        {"driver_id": "D0", "lat": 40.742957786826175, "lon": -73.98643612651269},
        {"driver_id": "D1", "lat": 40.74982450326232, "lon": -74.00296405493984},
        {"driver_id": "D2", "lat": 40.76052708834015, "lon": -73.97990492898906},
        {"driver_id": "D3", "lat": 40.80405545840529, "lon": -73.95542202172038},
        {"driver_id": "D4", "lat": 40.79950553336733, "lon": -73.9434006827609},
        {"driver_id": "D5", "lat": 40.77961701572855, "lon": -73.9567577260492}
    ]
    return pd.DataFrame(data)

# =========================
# RIDERS DATASET
# =========================

def generate_riders_df(max_riders_per_location: int = 3, radius_km: float = RIDER_RADIUS_KM) -> pd.DataFrame:
    """
    Generate random riders around predefined static locations
    """
    # Static locations
    locations = [
        (40.731512260279096, -73.99523189848435),
        (40.748562576767355, -73.98756029618569),
        (40.77296792075795, -73.97144993135852),
        (40.80084876931885, -73.95252664568851),
        (40.81536540843218, -73.94357644300673),
        (40.836844207113565, -73.92669891736966),
        (40.82891140740017, -73.91058855254249)
    ]

    riders = []
    rider_id = 0

    for lat_center, lon_center in locations:
        n_riders = random.randint(1, max_riders_per_location)  # random riders per location
        for _ in range(n_riders):
            lat, lon = random_point(lat_center, lon_center, radius_km)
            riders.append({
                "rider_id": rider_id,
                "lat": lat,
                "lon": lon
            })
            rider_id += 1

    return pd.DataFrame(riders)

# # =========================
# # Example Usage
# # =========================

# if __name__ == "__main__":
#     riders_df = generate_riders_df(max_riders_per_location=3)
#     print(riders_df)
#     print("Total riders generated:", len(riders_df))
