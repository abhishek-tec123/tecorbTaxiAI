"""
Production-ready data seeding module for DRIVERS and RIDERS.
Safe to import and reuse.

- Uses NYC polygon sampling
- Batch inserts
- Deterministic activity dates
"""

from __future__ import annotations

import uuid
import random
import json
import time
from datetime import datetime, date
from math import ceil
from typing import Iterable, List, Tuple

from db_config import get_connection as mysql_get_connection
from faker import Faker
from h3 import h3
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon as ShapelyPolygon

from schema import ALL_TABLES
from helpers import (
    generate_driver_activity_datetimes,
    generate_rider_activity_datetimes,
)
from nyc_polygon import NYC_POLYGON, MIN_LAT, MAX_LAT, MIN_LON, MAX_LON

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
NUM_DRIVERS = 7_950
NUM_RIDERS = 7_590
BATCH_SIZE = 500
H3_RESOLUTION = 7
TARGET_ACTIVITY_DATE = date(2025, 11, 17)

fake = Faker()


# -----------------------------------------------------------------------------
# Database utilities
# -----------------------------------------------------------------------------
def get_connection():
    return mysql_get_connection()


def create_tables(conn) -> None:
    cur = conn.cursor()
    for ddl in ALL_TABLES:
        cur.execute(ddl)
    conn.commit()
    cur.close()


# -----------------------------------------------------------------------------
# Geography helpers
# -----------------------------------------------------------------------------
def random_nyc_point() -> Tuple[float, float]:
    """Sample a random point strictly inside NYC polygon."""
    while True:
        lat = random.uniform(MIN_LAT, MAX_LAT)
        lon = random.uniform(MIN_LON, MAX_LON)
        if NYC_POLYGON.contains(Point(lon, lat)):
            return lat, lon


def random_point_in_h3(hex_id: str) -> Tuple[float, float]:
    boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
    poly = ShapelyPolygon(boundary)
    min_lon, min_lat, max_lon, max_lat = poly.bounds

    for _ in range(200):
        lon = random.uniform(min_lon, max_lon)
        lat = random.uniform(min_lat, max_lat)
        if poly.contains(Point(lon, lat)):
            return lat, lon

    centroid = poly.centroid
    return centroid.y, centroid.x


# -----------------------------------------------------------------------------
# H3 helpers
# -----------------------------------------------------------------------------
def get_random_h3_batch(conn, n: int) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        f"SELECT hex_id FROM h3_hexes WHERE resolution={H3_RESOLUTION} ORDER BY RAND() LIMIT {n}"
    )
    rows = [r[0] for r in cur.fetchall()]
    cur.close()

    if not rows:
        raise RuntimeError("No H3 hexes found for resolution " + str(H3_RESOLUTION))

    while len(rows) < n:
        rows.append(random.choice(rows))

    return rows


# -----------------------------------------------------------------------------
# Driver logic
# -----------------------------------------------------------------------------
def build_driver_row(lat, lon, h3_id, activity_at):
    return (
        str(uuid.uuid4()),
        f"D-{uuid.uuid4()}",
        fake.name(),
        fake.phone_number(),
        None,
        random.choice(["idle", "offline"]),
        h3_id,
        lat,
        lon,
        round(random.uniform(3.5, 5.0), 2),
        activity_at,
        datetime.utcnow(),
        datetime.utcnow(),
        json.dumps({}),
    )


def insert_drivers(conn, n: int, activity_date: date) -> None:
    sql = """
    INSERT INTO drivers (
        driver_id, external_id, name, phone, vehicle_id,
        status, current_h3, lat, lon, rating,
        activity_at, last_update_at, created_at, meta
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cur = conn.cursor()
    activity_times = generate_driver_activity_datetimes(activity_date, n)
    inserted = 0

    for _ in range(ceil(n / BATCH_SIZE)):
        batch = min(BATCH_SIZE, n - inserted)
        hexes = get_random_h3_batch(conn, batch)
        rows = []

        for i, h3_hex in enumerate(hexes):
            lat, lon = random_nyc_point()
            rows.append(build_driver_row(lat, lon, h3_hex, activity_times[inserted + i]))

        cur.executemany(sql, rows)
        conn.commit()
        inserted += len(rows)
        print(f"Drivers inserted: {inserted}/{n}")

    cur.close()


# -----------------------------------------------------------------------------
# Rider logic
# -----------------------------------------------------------------------------
def build_rider_row(activity_at):
    lat, lon = random_nyc_point()
    return (
        str(uuid.uuid4()),
        f"R-{uuid.uuid4()}",
        fake.name(),
        fake.phone_number(),
        lat,
        lon,
        activity_at,
        datetime.utcnow(),
        json.dumps({}),
    )


def insert_riders(conn, n: int, activity_date: date) -> None:
    sql = """
    INSERT INTO riders (
        rider_id, external_id, name, phone,
        lat, lon, activity_at, created_at, meta
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    cur = conn.cursor()
    activity_times = generate_rider_activity_datetimes(activity_date, n)
    inserted = 0

    for _ in range(ceil(n / BATCH_SIZE)):
        batch = min(BATCH_SIZE, n - inserted)
        rows = [build_rider_row(activity_times[inserted + i]) for i in range(batch)]
        cur.executemany(sql, rows)
        conn.commit()
        inserted += len(rows)
        print(f"Riders inserted: {inserted}/{n}")

    cur.close()


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def seed_drivers_and_riders(
    drivers: int = NUM_DRIVERS,
    riders: int = NUM_RIDERS,
    activity_date: date = TARGET_ACTIVITY_DATE,
) -> None:
    conn = get_connection()
    try:
        create_tables(conn)
        insert_drivers(conn, drivers, activity_date)
        insert_riders(conn, riders, activity_date)
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    start = time.time()
    seed_drivers_and_riders()
    print(f"Seeding completed in {time.time() - start:.1f}s")


# if __name__ == "__main__":
#     main()
