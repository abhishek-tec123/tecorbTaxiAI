import pandas as pd
import random
import math
from typing import Tuple

# =========================
# CONFIG
# =========================

CITY_CENTER = (40.74, -73.98)
RIDER_RADIUS_KM = 2

# =========================
# GEO UTIL
# =========================

def random_point(lat: float, lon: float, radius_km: float) -> Tuple[float, float]:
    r = radius_km / 111
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
    ]
    return pd.DataFrame(data)

# =========================
# RIDERS DATASET
# =========================

def generate_riders_df(n: int) -> pd.DataFrame:
    """
    Generate n random riders
    """
    riders = []
    for i in range(n):
        lat, lon = random_point(*CITY_CENTER, RIDER_RADIUS_KM)
        riders.append({
            "rider_id": i,
            "lat": lat,
            "lon": lon
        })
    return pd.DataFrame(riders)
