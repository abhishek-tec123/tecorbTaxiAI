"""
Production-ready script to compute DAILY H3 counts for riders or drivers
and store them in fixed-schema MySQL tables.
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
from h3 import h3
from collections import Counter
from datetime import datetime, date
from typing import Dict, Iterable

from schema import HEX_LIST

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
H3_RESOLUTION = 7
BATCH_SIZE = 10_000

ENTITY_CONFIG = {
    "riders": {
        "source_table": "riders",
        "target_table": "rider_hex_daily_fixed",
    },
    "drivers": {
        "source_table": "drivers",
        "target_table": "drivers_hex_daily_fixed",
    },
}


# -----------------------------------------------------------------------------
# Database utilities
# -----------------------------------------------------------------------------
def get_connection():
    return mysql_get_connection()


def stream_rows(cursor, batch_size: int = BATCH_SIZE) -> Iterable[Dict]:
    """Stream rows from MySQL cursor safely."""
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
    """Create a fixed-schema DAILY H3 table if it does not exist."""
    columns = ",\n    ".join(f"h_{h} INT DEFAULT 0" for h in HEX_LIST)

    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        report_date DATE NOT NULL,
        {columns},
        PRIMARY KEY (report_date)
    ) ENGINE=InnoDB;
    """
    cursor.execute(sql)


# -----------------------------------------------------------------------------
# Core logic
# -----------------------------------------------------------------------------
def fetch_daily_positions(cursor, source_table: str, target_date: date) -> None:
    """Fetch lat/lon rows for a specific date."""
    cursor.execute(
        f"""
        SELECT lat, lon
        FROM {source_table}
        WHERE DATE(activity_at) = %s
        """,
        (target_date,),
    )


def compute_daily_h3_counts(cursor) -> Counter:
    """Compute Counter({h3_index: count}) for the day."""
    counts: Counter = Counter()

    for row in stream_rows(cursor):
        lat = row["lat"]
        lon = row["lon"]

        if lat is None or lon is None:
            continue

        h3_index = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
        if h3_index in HEX_LIST:
            counts[h3_index] += 1

    return counts


def upsert_daily_counts(
    cursor,
    table_name: str,
    report_date: date,
    counts: Counter,
) -> None:
    """Insert base row and update fixed H3 columns."""
    cursor.execute(
        f"INSERT IGNORE INTO {table_name} (report_date) VALUES (%s)",
        (report_date.isoformat(),),
    )

    for h in HEX_LIST:
        cursor.execute(
            f"""
            UPDATE {table_name}
            SET h_{h} = %s
            WHERE report_date = %s
            """,
            (counts.get(h, 0), report_date.isoformat()),
        )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def process_entity(entity: str, target_date: date) -> None:
    """End-to-end DAILY processing for one entity."""
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unsupported entity: {entity}")

    cfg = ENTITY_CONFIG[entity]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        create_daily_table(cursor, cfg["target_table"])
        fetch_daily_positions(cursor, cfg["source_table"], target_date)
        counts = compute_daily_h3_counts(cursor)
        upsert_daily_counts(cursor, cfg["target_table"], target_date, counts)
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
        print(f"Daily H3 counts completed for {entity} on {TARGET_DATE_STR}")


# if __name__ == "__main__":
#     main()
