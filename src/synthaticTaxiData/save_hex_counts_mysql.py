"""
Production-ready module to compute DAILY and HOURLY trip, rider, and driver
counts per fixed H3 hex and store them in MySQL tables.

Safe to import and reuse.
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
import h3
import csv
import os
from collections import Counter, defaultdict
from datetime import datetime, date
from typing import Dict, Iterable, Tuple, Set
# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BATCH_SIZE = 10_000

# Load hex IDs from CSV file
def load_hex_ids_from_csv(csv_path: str) -> Tuple[Set[str], int]:
    """
    Load hex IDs and resolution from intersected_hexes.csv.
    Returns (set of hex_ids, resolution).
    """
    hex_ids = set()
    resolution = None
    
    # Get the absolute path relative to this file's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, '..', '..', 'map_file', 'intersected_hexes.csv')
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            hex_id = row['hex_id'].strip()
            if hex_id:
                hex_ids.add(hex_id)
                if resolution is None:
                    resolution = int(row['resolution'])
    
    return hex_ids, resolution

FIXED_HEX_IDS_SET, H3_RESOLUTION = load_hex_ids_from_csv('intersected_hexes.csv')
FIXED_HEX_IDS = sorted(list(FIXED_HEX_IDS_SET))  # Keep as list for iteration order

# Verify loading
if not FIXED_HEX_IDS_SET:
    raise ValueError("No hex IDs loaded from CSV file!")
if H3_RESOLUTION is None:
    raise ValueError("Could not determine resolution from CSV file!")
print(f"Loaded {len(FIXED_HEX_IDS_SET)} hex IDs at resolution {H3_RESOLUTION}")

# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------
def get_connection():
    return mysql_get_connection()


def stream_rows(cursor, batch_size: int = BATCH_SIZE) -> Iterable[Tuple]:
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            yield row

# -----------------------------------------------------------------------------
# Schema management
# -----------------------------------------------------------------------------
def create_daily_table(cursor, table_name: str) -> None:
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in FIXED_HEX_IDS)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            trip_date DATE NOT NULL,
            {columns},
            PRIMARY KEY (trip_date)
        ) ENGINE=InnoDB;
        """
    )


def create_hourly_table(cursor, table_name: str) -> None:
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in FIXED_HEX_IDS)
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            trip_date DATE NOT NULL,
            trip_hour TINYINT NOT NULL,
            {columns},
            PRIMARY KEY (trip_date, trip_hour)
        ) ENGINE=InnoDB;
        """
    )

# -----------------------------------------------------------------------------
# Fetchers
# -----------------------------------------------------------------------------
def fetch_trip_daily(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT pickup_lat, pickup_lon
        FROM trips
        WHERE DATE(start_at) = %s
        """,
        (trip_date,),
    )


def fetch_trip_hourly(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT pickup_lat, pickup_lon, HOUR(start_at)
        FROM trips
        WHERE DATE(start_at) = %s
        """,
        (trip_date,),
    )


def fetch_rider_daily(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT lat, lon
        FROM riders
        WHERE DATE(activity_at) = %s
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        """,
        (trip_date,),
    )


def fetch_rider_hourly(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT lat, lon, HOUR(activity_at)
        FROM riders
        WHERE DATE(activity_at) = %s
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        """,
        (trip_date,),
    )


def fetch_driver_daily(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT lat, lon
        FROM drivers
        WHERE DATE(activity_at) = %s
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        """,
        (trip_date,),
    )


def fetch_driver_hourly(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT lat, lon, HOUR(activity_at)
        FROM drivers
        WHERE DATE(activity_at) = %s
          AND lat IS NOT NULL
          AND lon IS NOT NULL
        """,
        (trip_date,),
    )

# -----------------------------------------------------------------------------
# Counters
# -----------------------------------------------------------------------------
def count_daily(cursor) -> Counter:
    counts: Counter = Counter()
    for lat, lon in stream_rows(cursor):
        try:
            hid = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
            if hid in FIXED_HEX_IDS_SET:
                counts[hid] += 1
        except Exception:
            continue
    return counts


def count_hourly(cursor) -> Dict[int, Counter]:
    hourly: Dict[int, Counter] = defaultdict(Counter)
    for lat, lon, hour in stream_rows(cursor):
        try:
            hid = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
            if hid in FIXED_HEX_IDS_SET:
                hourly[hour][hid] += 1
        except Exception:
            continue
    return hourly

# -----------------------------------------------------------------------------
# Writers
# -----------------------------------------------------------------------------
def upsert_daily(cursor, table: str, trip_date: date, counts: Counter) -> None:
    cursor.execute(
        f"INSERT IGNORE INTO {table} (trip_date) VALUES (%s)",
        (trip_date,),
    )
    for h in FIXED_HEX_IDS:
        cursor.execute(
            f"UPDATE {table} SET h_{h}=%s WHERE trip_date=%s",
            (counts.get(h, 0), trip_date),
        )


def upsert_hourly(cursor, table: str, trip_date: date, hourly: Dict[int, Counter]) -> None:
    for hour in range(24):
        cursor.execute(
            f"INSERT IGNORE INTO {table} (trip_date, trip_hour) VALUES (%s, %s)",
            (trip_date, hour),
        )
        for h in FIXED_HEX_IDS:
            cursor.execute(
                f"""
                UPDATE {table}
                SET h_{h}=%s
                WHERE trip_date=%s AND trip_hour=%s
                """,
                (hourly.get(hour, {}).get(h, 0), trip_date, hour),
            )

# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def process_trip_daily(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_daily_table(cur, "trip_daily_hex_counts")
        fetch_trip_daily(cur, trip_date)
        upsert_daily(cur, "trip_daily_hex_counts", trip_date, count_daily(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_trip_hourly(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_hourly_table(cur, "trip_hourly_hex_counts")
        fetch_trip_hourly(cur, trip_date)
        upsert_hourly(cur, "trip_hourly_hex_counts", trip_date, count_hourly(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_rider_daily(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_daily_table(cur, "rider_daily_hex_counts")
        fetch_rider_daily(cur, trip_date)
        upsert_daily(cur, "rider_daily_hex_counts", trip_date, count_daily(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_rider_hourly(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_hourly_table(cur, "rider_hourly_hex_counts")
        fetch_rider_hourly(cur, trip_date)
        upsert_hourly(cur, "rider_hourly_hex_counts", trip_date, count_hourly(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_driver_daily(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_daily_table(cur, "driver_daily_hex_counts")
        fetch_driver_daily(cur, trip_date)
        upsert_daily(cur, "driver_daily_hex_counts", trip_date, count_daily(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def process_driver_hourly(trip_date: date):
    conn = get_connection()
    cur = conn.cursor()
    try:
        create_hourly_table(cur, "driver_hourly_hex_counts")
        fetch_driver_hourly(cur, trip_date)
        upsert_hourly(cur, "driver_hourly_hex_counts", trip_date, count_hourly(cur))
        conn.commit()
    finally:
        cur.close()
        conn.close()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    TARGET_DATE_STR = "2025-07-07"
    trip_date = datetime.strptime(TARGET_DATE_STR, "%Y-%m-%d").date()

    process_trip_daily(trip_date)
    process_trip_hourly(trip_date)

    process_rider_daily(trip_date)
    process_rider_hourly(trip_date)

    process_driver_daily(trip_date)
    process_driver_hourly(trip_date)

    print(f"H3 aggregation completed for {TARGET_DATE_STR}")


# if __name__ == "__main__":
#     main()
