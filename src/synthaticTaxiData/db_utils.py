"""
Database helpers for taxi simulation scripts (MySQL).
"""
import random
from datetime import datetime

from schema import TRIP_MATCH_LOGS_TABLE
from helpers import bbox_for_distance, haversine_km
from db_config import get_connection

try:
    from h3 import h3
except ImportError:
    raise ImportError("Please install h3: pip install h3==3.7.6")

H3_RES = 7
MATCH_LOG_TABLE = "trip_match_logs"
MATCH_LOG_TABLE_READY = False


def get_conn():
    """
    MySQL connection with dict rows (similar to sqlite3.Row).
    """
    return get_connection()


def ensure_match_log_table(conn):
    """
    Create the trip_match_logs table the first time we need it.
    """
    global MATCH_LOG_TABLE_READY
    if MATCH_LOG_TABLE_READY:
        return

    cur = conn.cursor()
    cur.execute(TRIP_MATCH_LOGS_TABLE)
    conn.commit()
    cur.close()
    MATCH_LOG_TABLE_READY = True


def fetch_one_rider(conn):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM riders ORDER BY RAND() LIMIT 1")
    row = cur.fetchone()
    cur.close()
    return row


def fetch_drivers_in_bbox(conn, min_lat, max_lat, min_lon, max_lon, limit=2000):
    cur = conn.cursor(dictionary=True)
    sql = """
    SELECT driver_id, lat, lon, current_h3, last_update_at
    FROM drivers
    WHERE lat BETWEEN %s AND %s
      AND lon BETWEEN %s AND %s
    LIMIT %s
    """
    cur.execute(sql, (min_lat, max_lat, min_lon, max_lon, limit))
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_driver_within_distance(conn, pickup_lat, pickup_lon, max_distance_km=10):
    """
    Use bounding-box prefilter + haversine distance to grab a nearby driver.
    """
    min_lat, max_lat, min_lon, max_lon = bbox_for_distance(pickup_lat, pickup_lon, max_distance_km)
    candidates = fetch_drivers_in_bbox(conn, min_lat, max_lat, min_lon, max_lon)

    nearby = []
    for driver in candidates:
        dlat = driver["lat"]
        dlon = driver["lon"]
        dist = haversine_km(pickup_lat, pickup_lon, dlat, dlon)

        if dist <= max_distance_km:
            driver["distance_to_pickup_km"] = dist
            nearby.append(driver)


    if not nearby:
        return None

    return random.choice(nearby)


def insert_trip(conn, trip, *, commit=True):
    sql = """
    INSERT INTO trips (
        trip_id, request_id, rider_id, driver_id,
        status, requested_at, matched_at, start_at, end_at,
        pickup_lat, pickup_lon, drop_lat, drop_lon,
        pickup_distance_km, ride_distance_km, ride_duration_min,
        wait_time_min, fare, cancellation_reason,
        match_quality, created_at, meta
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
              %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
              %s,%s,%s)
    """
    cur = conn.cursor()
    cur.execute(sql, trip)
    if commit:
        conn.commit()
    cur.close()


def update_trip_fields(conn, trip_id, commit=True, **fields):
    if not fields:
        return

    assignments = ", ".join(f"{col}=%s" for col in fields)
    sql = f"UPDATE trips SET {assignments} WHERE trip_id=%s"
    params = list(fields.values()) + [trip_id]

    cur = conn.cursor()
    cur.execute(sql, params)
    if commit:
        conn.commit()
    cur.close()


def log_match_event(
    conn,
    *,
    trip_id,
    driver_id,
    rider_id,
    distance_km,
    match_status,
    matcher_version,
    reward_estimate=None,
    response_time_ms=None,
    commit=True
):
    """
    Persist a match attempt for observability and reinforcement learning features.
    """
    ensure_match_log_table(conn)

    sql = f"""
    INSERT INTO {MATCH_LOG_TABLE} (
        trip_id, ts, driver_id, rider_id,
        distance_km, match_status,
        matcher_version, reward_estimate, response_time_ms
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    row = (
        trip_id,
        datetime.utcnow(),
        driver_id,
        rider_id,
        distance_km,
        match_status,
        matcher_version,
        reward_estimate,
        response_time_ms
    )
    cur = conn.cursor()
    cur.execute(sql, row)
    if commit:
        conn.commit()
    cur.close()


def update_driver_location(conn, driver_id, lat, lon, *, commit=True):
    now = datetime.utcnow()
    new_h3 = h3.geo_to_h3(lat, lon, H3_RES)
    sql = "UPDATE drivers SET lat=%s, lon=%s, current_h3=%s, last_update_at=%s WHERE driver_id=%s"
    cur = conn.cursor()
    cur.execute(sql, (lat, lon, new_h3, now.isoformat(), driver_id))
    if commit:
        conn.commit()
    cur.close()
    return {
        "driver_id": driver_id,
        "lat": lat,
        "lon": lon,
        "current_h3": new_h3,
        "last_update_at": now
    }

def create_forecast_table_with_hex_columns():
    """
    Dynamically create a forecasts table where each hex_id from h3_hexes becomes a column.
    Column name = original hex_id.
    """
    conn = get_conn()
    cursor = conn.cursor()

    # 1. Fetch all hex_ids
    cursor.execute("SELECT hex_id FROM h3_hexes ORDER BY id")
    hex_ids = [row[0] for row in cursor.fetchall()]

    if not hex_ids:
        cursor.close()
        conn.close()
        raise ValueError("No hex_ids found in h3_hexes table.")

    # 2. Build columns: use hex_id as column name
    hex_columns = ",\n".join([f"`{hex_id}` DOUBLE" for hex_id in hex_ids])

    # 3. Create forecasts table
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS forecasts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        Date_time DATETIME NOT NULL,
        {hex_columns},
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """

    cursor.execute(create_table_sql)
    conn.commit()

    cursor.close()
    conn.close()

    # Return mapping (hex_id -> hex_id column name)
    hex_column_map = {hex_id: hex_id for hex_id in hex_ids}
    return hex_column_map
