from __future__ import annotations

import os
from datetime import datetime, date

try:
    from h3 import h3
except ImportError:
    raise ImportError("Please install h3: pip install h3==3.7.6")

# Project base and src layout
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
DATA_DIR = os.path.join(SRC_DIR, "synthaticTaxiData")
DB_NAME = os.getenv("MYSQL_DB", "taxiProduction")

import sys

# Ensure `src` and the moved `synthaticTaxiData` package are importable
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)
if DATA_DIR not in sys.path:
    sys.path.append(DATA_DIR)

from schema import ALL_TABLES, HEX_LIST  # type: ignore
import rider_driver  # type: ignore
import trip  # type: ignore
import save_hex_counts_mysql  # type: ignore
import store_daily_count_rid_dri_perhex  # type: ignore
import store_hrly_count_rid_dri_perhex  # type: ignore
from db_config import get_connection as mysql_get_connection  # type: ignore


def get_conn():
    return mysql_get_connection()


def init_db() -> None:
    """
    Create core tables (drivers, riders, trips, trip_match_logs, h3_hexes)
    and populate h3_hexes from HEX_LIST.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Create tables
    for ddl in ALL_TABLES:
        cur.execute(ddl)

    # Populate h3_hexes with basic metadata for each hex in HEX_LIST
    # (center_lat/lon, area, etc.).
    conn.commit()

    # Minimal insert (resolution=7, center lat/lon, area from h3)
    try:
        area_km2 = h3.hex_area(resolution=7, unit="km2")
    except Exception:
        try:
            area_km2 = h3.hex_area(7, "km2")
        except Exception:
            area_km2 = h3.hex_area(7)
    area_m2 = area_km2 * 1_000_000.0

    insert_sql = """
    INSERT IGNORE INTO h3_hexes (
        hex_id, resolution, center_lat, center_lon,
        area_km2, area_m2, edge_length_km,
        inside_polygon, point_hex, driver_count, rider_count, created_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    from datetime import datetime as _dt

    now_str = _dt.utcnow().isoformat()

    for hex_id in HEX_LIST:
        lat, lon = h3.h3_to_geo(hex_id)
        # edge length in km, robust to API differences
        try:
            edge_km = h3.edge_length(resolution=7, unit="km")
        except Exception:
            try:
                edge_km = h3.edge_length(7, "km")
            except Exception:
                edge_km = h3.edge_length(7)

        cur.execute(
            insert_sql,
            (
                hex_id,
                7,
                lat,
                lon,
                area_km2,
                area_m2,
                edge_km,
                1,
                1,
                0,
                0,
                now_str,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Initialized database '{DB_NAME}' with core tables and {len(HEX_LIST)} hexes.")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def seed(*, drivers: int = 7_950, riders: int = 7_590, activity_date: date) -> None:
    """
    Programmatic API: seed drivers and riders.

    Example (Python):
        from dataApp import seed
        from datetime import date
        seed(drivers=5000, riders=5000, activity_date=date(2025, 11, 17))
    """
    rider_driver.seed_drivers_and_riders(
        drivers=drivers,
        riders=riders,
        activity_date=activity_date,
    )


def generate_trips(
    *,
    trip_date: date,
    num_rides: int,
    batch_size: int = 1000,
    progress_every: int = 100,
    verbose: bool = False,
) -> None:
    """
    Programmatic API: generate trips for a given date.

    Example:
        from dataApp import generate_trips
        from datetime import date
        generate_trips(trip_date=date(2025, 11, 17), num_rides=3000)
    """
    trip.create_trips_for_date(
        target_date=trip_date,
        num_rides=num_rides,
        batch_size=batch_size,
        progress_every=progress_every,
        verbose=verbose,
    )


def aggregate(*, target_date: date) -> None:
    """
    Programmatic API: run all aggregations for a given date.

    Runs:
    - Trip H3 daily & hourly counts (save_hex_counts_mysql)
    - Rider/driver daily and hourly hex counts (store_daily_count_rid_dri_perhex,
      store_hrly_count_rid_dri_perhex)
    """
    target_date_str = target_date.strftime("%Y-%m-%d")
    print(f"Running trip H3 aggregations for {target_date_str}...")
    save_hex_counts_mysql.process_daily(target_date)
    save_hex_counts_mysql.process_hourly(target_date)

    # Entity-based (riders/drivers) daily & hourly hex counts
    for entity in ("riders", "drivers"):
        print(f"Running DAILY hex counts for {entity} on {target_date_str}...")
        store_daily_count_rid_dri_perhex.process_entity(entity, target_date)

    for entity in ("riders", "drivers"):
        print(f"Running HOURLY hex counts for {entity} on {target_date_str}...")
        store_hrly_count_rid_dri_perhex.process_entity(entity, target_date)

    print(f"All aggregations completed for {target_date_str}.")
# # insert with single single date-----------------------------------------------------
# def main() -> None:
#     """
#     Main execution entrypoint.

#     This will:
#     - Initialize the database
#     - Seed drivers and riders
#     - Generate trips
#     - Run all aggregations
#     """

#     # ---- CONFIG ----
#     ACTIVITY_DATE = date(2025, 7, 7)
#     NUM_DRIVERS = 3290
#     NUM_RIDERS = 3330
#     NUM_TRIPS = 10

#     print("🚕 Taxi Simulation Started")
#     print("=" * 50)

#     # 1️⃣ Initialize DB (idempotent)
#     print("Ensuring database schema exists...")
#     init_db()

#     # 2️⃣ Seed drivers & riders
#     print(f"Seeding {NUM_DRIVERS} drivers and {NUM_RIDERS} riders...")
#     seed(
#         drivers=NUM_DRIVERS,
#         riders=NUM_RIDERS,
#         activity_date=ACTIVITY_DATE,
#     )

#     # 3️⃣ Generate trips
#     print(f"Generating {NUM_TRIPS} trips for {ACTIVITY_DATE}...")
#     generate_trips(
#         trip_date=ACTIVITY_DATE,
#         num_rides=NUM_TRIPS,
#         batch_size=1000,
#         progress_every=100,
#         verbose=True,
#     )

#     # 4️⃣ Run aggregations
#     print("Running aggregations...")
#     aggregate(target_date=ACTIVITY_DATE)

#     print("=" * 50)
#     print("✅ Taxi Simulation Completed Successfully")


# if __name__ == "__main__":
#     main()


# insert with multiple date with random value

from datetime import date, timedelta
import random


def monday_range(start: date, end: date):
    """Yield every Monday from start to end (inclusive)."""
    current = start
    while current <= end:
        if current.weekday() == 0:  # Monday
            yield current
        current += timedelta(days=1)


def main() -> None:
    """
    Main execution entrypoint.

    This will:
    - Initialize the database (idempotent)
    - For every Monday in the given range:
        - Seed drivers and riders (randomized)
        - Generate trips (fixed count)
        - Run aggregations
    """

    # ---- CONFIG ----
    START_DATE = date(2025, 7, 7)
    END_DATE = date(2025, 11, 17)

    RIDER_MIN = 2700
    RIDER_MAX = 3200

    DRIVER_GAP_MIN = 100   # drivers less than riders
    DRIVER_GAP_MAX = 200

    NUM_TRIPS = 10  # fixed trips per day

    print("🚕 Taxi Simulation Started")
    print("=" * 50)

    # 1️⃣ Initialize DB (idempotent)
    print("Ensuring database schema exists...")
    init_db()

    # 2️⃣ Process every Monday
    for activity_date in monday_range(START_DATE, END_DATE):
        riders = random.randint(RIDER_MIN, RIDER_MAX)
        drivers = riders - random.randint(DRIVER_GAP_MIN, DRIVER_GAP_MAX)

        print("\n" + "-" * 50)
        print(f"📅 Processing {activity_date}")
        print(f"Seeding {drivers} drivers and {riders} riders...")

        seed(
            drivers=drivers,
            riders=riders,
            activity_date=activity_date,
        )

        print(f"Generating {NUM_TRIPS} trips for {activity_date}...")
        generate_trips(
            trip_date=activity_date,
            num_rides=NUM_TRIPS,
            batch_size=1000,
            progress_every=100,
            verbose=True,
        )

        print("Running aggregations...")
        aggregate(target_date=activity_date)

    print("=" * 50)
    print("✅ Taxi Simulation Completed Successfully")


if __name__ == "__main__":
    main()
