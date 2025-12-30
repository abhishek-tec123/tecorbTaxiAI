"""
Production‑ready script to compute hourly H3 counts for riders or drivers
and store them in fixed‑schema MySQL tables.
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
from h3 import h3
from collections import defaultdict, Counter
from datetime import datetime, date
from typing import Dict, Iterable

from schema import HEX_LIST

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
H3_RESOLUTION = 7
BATCH_SIZE = 10_000

# Supported entities configuration
ENTITY_CONFIG = {
    "riders": {
        "source_table": "riders",
        "target_table": "rider_hex_hourly_fixed",
    },
    "drivers": {
        "source_table": "drivers",
        "target_table": "drivers_hex_hourly_fixed",
    },
}


# -----------------------------------------------------------------------------
# Database utilities
# -----------------------------------------------------------------------------
def get_connection():
    return mysql_get_connection()


def stream_rows(cursor, batch_size: int = BATCH_SIZE) -> Iterable[Dict]:
    """Stream rows from a MySQL cursor to avoid loading everything in memory."""
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            yield row


# -----------------------------------------------------------------------------
# Schema management
# -----------------------------------------------------------------------------
def create_hourly_table(cursor, table_name: str) -> None:
    """Create a fixed‑schema hourly H3 table if it does not exist."""
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in HEX_LIST)

    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        report_date DATE NOT NULL,
        hour TINYINT NOT NULL,
        {columns},
        PRIMARY KEY (report_date, hour)
    ) ENGINE=InnoDB;
    """
    cursor.execute(sql)


# -----------------------------------------------------------------------------
# Core logic
# -----------------------------------------------------------------------------
def fetch_hourly_positions(cursor, source_table: str, target_date: date) -> None:
    """Execute query to fetch lat/lon with hour for a given date."""
    cursor.execute(
        f"""
        SELECT lat, lon, HOUR(activity_at) AS hour
        FROM {source_table}
        WHERE DATE(activity_at) = %s
        """,
        (target_date,),
    )


def compute_hourly_h3_counts(cursor) -> Dict[int, Counter]:
    """Compute {hour: Counter({h3_index: count})}."""
    counts: Dict[int, Counter] = defaultdict(Counter)

    for row in stream_rows(cursor):
        lat = row["lat"]
        lon = row["lon"]
        hour = row["hour"]

        if lat is None or lon is None or hour is None:
            continue

        h3_index = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
        if h3_index in HEX_LIST:
            counts[hour][h3_index] += 1

    return counts


def upsert_hourly_counts(
    cursor,
    table_name: str,
    report_date: date,
    hourly_counts: Dict[int, Counter],
) -> None:
    """Insert base rows and update fixed H3 columns."""
    for hour, hex_counter in hourly_counts.items():
        cursor.execute(
            f"""
            INSERT IGNORE INTO {table_name} (report_date, hour)
            VALUES (%s, %s)
            """,
            (report_date.isoformat(), hour),
        )

        for h in HEX_LIST:
            cursor.execute(
                f"""
                UPDATE {table_name}
                SET h_{h} = %s
                WHERE report_date = %s AND hour = %s
                """,
                (hex_counter.get(h, 0), report_date.isoformat(), hour),
            )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def process_entity(entity: str, target_date: date) -> None:
    """End‑to‑end processing for a single entity (riders or drivers)."""
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unsupported entity: {entity}")

    cfg = ENTITY_CONFIG[entity]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        create_hourly_table(cursor, cfg["target_table"])
        fetch_hourly_positions(cursor, cfg["source_table"], target_date)
        hourly_counts = compute_hourly_h3_counts(cursor)
        upsert_hourly_counts(cursor, cfg["target_table"], target_date, hourly_counts)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
def main() -> None:
    TARGET_DATE_STR = "2025-11-17"
    target_date = datetime.strptime(TARGET_DATE_STR, "%Y-%m-%d").date()

    for entity in ("riders", "drivers"):
        process_entity(entity, target_date)
        print(f"Hourly H3 counts completed for {entity} on {TARGET_DATE_STR}")


# if __name__ == "__main__":
#     main()
