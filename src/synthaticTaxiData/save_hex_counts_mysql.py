"""
Production-ready module to compute DAILY and HOURLY trip counts per fixed H3 hex
and store them in MySQL tables.

Safe to import and reuse.
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
import h3
from collections import Counter, defaultdict
from datetime import datetime, date
from typing import Dict, Iterable, Tuple

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
H3_RESOLUTION = 6
BATCH_SIZE = 10_000

FIXED_HEX_IDS = [
    "862a100f7ffffff", "862a1005fffffff", "862a100c7ffffff",
    "862a100d7ffffff", "862a100dfffffff", "862a1018fffffff",
    "862a100e7ffffff", "862a1000fffffff", "862a100efffffff",
    "862a103b7ffffff", "862a1001fffffff", "862a10017ffffff",
    "862a10037ffffff", "862a100afffffff", "862a10057ffffff",
    "862a103a7ffffff", "862a100cfffffff", "862a100a7ffffff",
    "862a10087ffffff", "862a1008fffffff", "862a10007ffffff",
    "862a1072fffffff", "862a10727ffffff",
]


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
def create_daily_table(cursor) -> None:
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in FIXED_HEX_IDS)
    sql = f"""
    CREATE TABLE IF NOT EXISTS daily_hex_counts (
        trip_date DATE NOT NULL,
        {columns},
        PRIMARY KEY (trip_date)
    ) ENGINE=InnoDB;
    """
    cursor.execute(sql)


def create_hourly_table(cursor) -> None:
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in FIXED_HEX_IDS)
    sql = f"""
    CREATE TABLE IF NOT EXISTS hourly_hex_counts (
        trip_date DATE NOT NULL,
        trip_hour TINYINT NOT NULL,
        {columns},
        PRIMARY KEY (trip_date, trip_hour)
    ) ENGINE=InnoDB;
    """
    cursor.execute(sql)


# -----------------------------------------------------------------------------
# Fetchers
# -----------------------------------------------------------------------------
def fetch_daily_trips(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT pickup_lat, pickup_lon
        FROM trips
        WHERE DATE(start_at) = %s
        """,
        (trip_date,),
    )


def fetch_hourly_trips(cursor, trip_date: date) -> None:
    cursor.execute(
        """
        SELECT pickup_lat, pickup_lon, HOUR(start_at)
        FROM trips
        WHERE DATE(start_at) = %s
        """,
        (trip_date,),
    )


# -----------------------------------------------------------------------------
# Counters
# -----------------------------------------------------------------------------
def count_daily(cursor) -> Counter:
    counts: Counter = Counter()

    for lat, lon in stream_rows(cursor):
        if lat is None or lon is None:
            continue
        try:
            hid = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
            if hid in FIXED_HEX_IDS:
                counts[hid] += 1
        except Exception:
            continue

    return counts


def count_hourly(cursor) -> Dict[int, Counter]:
    hourly: Dict[int, Counter] = defaultdict(Counter)

    for lat, lon, hour in stream_rows(cursor):
        if lat is None or lon is None or hour is None:
            continue
        try:
            hid = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
            if hid in FIXED_HEX_IDS:
                hourly[hour][hid] += 1
        except Exception:
            continue

    return hourly


# -----------------------------------------------------------------------------
# Writers
# -----------------------------------------------------------------------------
def upsert_daily(cursor, trip_date: date, counts: Counter) -> None:
    cursor.execute(
        "INSERT IGNORE INTO daily_hex_counts (trip_date) VALUES (%s)",
        (trip_date.isoformat(),),
    )

    for h in FIXED_HEX_IDS:
        cursor.execute(
            f"UPDATE daily_hex_counts SET h_{h}=%s WHERE trip_date=%s",
            (counts.get(h, 0), trip_date.isoformat()),
        )


def upsert_hourly(cursor, trip_date: date, hourly: Dict[int, Counter]) -> None:
    for hour in range(24):
        cursor.execute(
            "INSERT IGNORE INTO hourly_hex_counts (trip_date, trip_hour) VALUES (%s,%s)",
            (trip_date.isoformat(), hour),
        )

        for h in FIXED_HEX_IDS:
            cursor.execute(
                f"""
                UPDATE hourly_hex_counts
                SET h_{h}=%s
                WHERE trip_date=%s AND trip_hour=%s
                """,
                (hourly.get(hour, {}).get(h, 0), trip_date.isoformat(), hour),
            )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def process_daily(trip_date: date) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        create_daily_table(cursor)
        fetch_daily_trips(cursor, trip_date)
        counts = count_daily(cursor)
        upsert_daily(cursor, trip_date, counts)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def process_hourly(trip_date: date) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        create_hourly_table(cursor)
        fetch_hourly_trips(cursor, trip_date)
        hourly = count_hourly(cursor)
        upsert_hourly(cursor, trip_date, hourly)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    TARGET_DATE_STR = "2025-11-17"
    trip_date = datetime.strptime(TARGET_DATE_STR, "%Y-%m-%d").date()

    process_daily(trip_date)
    process_hourly(trip_date)

    print(f"Trip H3 aggregation completed for {TARGET_DATE_STR}")


# if __name__ == "__main__":
#     main()
