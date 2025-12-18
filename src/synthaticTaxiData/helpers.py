"""
Shared helper utilities for trip generation and geometry calculations.
"""
import random
from math import radians, cos, sin, asin, sqrt

from shapely.geometry import Point, Polygon

# NYC boundary (rough bounding polygon)
NYC_POLYGON = Polygon([
    (40.917103224942636, -73.91759745301404),
    (40.70407770535266, -74.02755646038577),
    (40.65281922768539, -73.72491699055529),
    (40.88736658837979, -73.81570883150444)
])

MIN_LAT = min(p[0] for p in NYC_POLYGON.exterior.coords)
MAX_LAT = max(p[0] for p in NYC_POLYGON.exterior.coords)
MIN_LON = min(p[1] for p in NYC_POLYGON.exterior.coords)
MAX_LON = max(p[1] for p in NYC_POLYGON.exterior.coords)


def random_nyc_point():
    """Return a random point contained inside the NYC polygon."""
    while True:
        lat = random.uniform(MIN_LAT, MAX_LAT)
        lon = random.uniform(MIN_LON, MAX_LON)
        if NYC_POLYGON.contains(Point(lat, lon)):
            return lat, lon


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two geo coordinates in kilometers."""
    radius_km = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


def bbox_for_distance(lat, lon, km):
    """
    Approximate bounding box (min_lat, max_lat, min_lon, max_lon)
    surrounding `km` radius around a coordinate.
    """
    delta_lat = km / 111.0
    delta_lon = km / (111.0 * cos(radians(lat)) + 1e-9)
    return lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon


def generate_drop_point(pickup_lat, pickup_lon, distance_km):
    """
    Produce a drop-off point roughly `distance_km` away while staying inside the NYC polygon.
    """
    delta_deg_drop = distance_km / 111.0
    while True:
        drop_lat = pickup_lat + random.uniform(-delta_deg_drop, delta_deg_drop)
        drop_lon = pickup_lon + random.uniform(-delta_deg_drop, delta_deg_drop)
        if NYC_POLYGON.contains(Point(drop_lat, drop_lon)):
            return drop_lat, drop_lon

import random
from datetime import datetime, timedelta, time

def random_time_between(start: time, end: time, base_date: datetime):
    """
    Return a random datetime between two times.
    Handles time ranges that cross midnight.
    """
    if start <= end:
        start_dt = datetime.combine(base_date.date(), start)
        end_dt = datetime.combine(base_date.date(), end)
    else:
        start_dt = datetime.combine(base_date.date(), start)
        end_dt = datetime.combine(base_date.date(), end) + timedelta(days=1)

    delta = end_dt - start_dt
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start_dt + timedelta(seconds=random_seconds)


import random
from datetime import datetime, date, time, timedelta


def generate_trip_datetime(target_date: date, num_trips: int, randomize_within_bucket: bool = True):
    """
    Generate a list of trip datetimes following:
      - 30% → 6–10 AM
      - 30% → 6–10 PM
      - 20% → 10 AM–6 PM
      - 10% → 10 PM–12 AM
      - 10% → 12 AM–6 AM

    If randomize_within_bucket = False → times are evenly spaced (serial).
    """

    buckets = [
        (0.30, (time(6, 0),  time(10, 0))),        # Morning peak
        (0.30, (time(18, 0), time(22, 0))),        # Evening peak
        (0.20, (time(10, 0), time(18, 0))),        # Midday
        (0.10, (time(22, 0), time(23, 59, 59))),   # Late night
        (0.10, (time(0, 0),  time(6, 0))),         # Midnight–early morning
    ]

    # ---- trips per bucket ----
    counts = [int(num_trips * ratio) for ratio, _ in buckets]

    # Fix rounding mismatch
    diff = num_trips - sum(counts)
    if diff != 0:
        counts[0] += diff

    datetimes = []

    # ---- evenly spaced inside a bucket ----
    def evenly_spaced(start_t, end_t, n):
        if n == 1:
            return [datetime.combine(target_date, start_t)]

        start_dt = datetime.combine(target_date, start_t)
        end_dt   = datetime.combine(target_date, end_t)

        # Midnight crossover (00:00–06:00)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        total_sec = (end_dt - start_dt).total_seconds()
        step_sec = total_sec / (n - 1)

        times = [start_dt + timedelta(seconds=i * step_sec) for i in range(n)]
        return times

    # ---- generate timestamps ----
    for (count, (t_start, t_end)) in zip(counts, [b[1] for b in buckets]):
        if count <= 0:
            continue

        if randomize_within_bucket:
            # Random timestamps inside the bucket
            for _ in range(count):

                start_sec = t_start.hour * 3600 + t_start.minute * 60 + t_start.second
                end_sec   = t_end.hour * 3600 + t_end.minute * 60 + t_end.second

                # Midnight wrap handling
                if end_sec < start_sec:
                    end_sec += 24 * 3600

                s = random.randint(start_sec, end_sec)
                s = s % (24 * 3600)

                dt = datetime.combine(target_date, time(s // 3600, (s // 60) % 60, s % 60))
                datetimes.append(dt)

        else:
            # Serial evenly spaced times
            datetimes.extend(evenly_spaced(t_start, t_end, count))

    datetimes.sort()
    return datetimes


def generate_driver_activity_datetimes(target_date: date, num_drivers: int):
    """
    Driver availability distribution (same buckets as trips).
    """
    return generate_trip_datetime(target_date, num_drivers, randomize_within_bucket=True)


def generate_rider_activity_datetimes(target_date: date, num_riders: int):
    """
    Rider activity distribution (same buckets as trips).
    """
    return generate_trip_datetime(target_date, num_riders, randomize_within_bucket=True)

# ---------------------------------------------------------
# Build trip blueprint (supports forced_timestamp)
# ---------------------------------------------------------
def build_trip_blueprint(pickup_lat, pickup_lon, forced_timestamp=None):
    if forced_timestamp:
        requested_at = forced_timestamp
    else:
        requested_at = generate_trip_datetime(date.today(), 1)[0]

    distance_km = round(random.uniform(3, 22), 2)
    drop_lat, drop_lon = generate_drop_point(pickup_lat, pickup_lon, distance_km)

    total_wait = random.uniform(0, 7)
    request_to_match = random.uniform(0.3 * total_wait, 0.7 * total_wait)
    match_to_start = total_wait - request_to_match

    matched_at = requested_at + timedelta(minutes=request_to_match)
    start_at = matched_at + timedelta(minutes=match_to_start)

    ride_duration_min = distance_km / 30.0 * 60.0
    end_at = start_at + timedelta(minutes=ride_duration_min)

    fare = round(3 + distance_km * 1.4 + random.uniform(0, 3), 2)
    match_quality = round(random.uniform(0.7, 0.99), 4)

    return {
        "distance_km": distance_km,
        "drop_lat": drop_lat,
        "drop_lon": drop_lon,
        "requested_at": requested_at,
        "total_wait": total_wait,
        "request_to_match": request_to_match,
        "match_to_start": match_to_start,
        "matched_at": matched_at,
        "start_at": start_at,
        "end_at": end_at,
        "ride_duration_min": ride_duration_min,
        "fare": fare,
        "match_quality": match_quality
    }
