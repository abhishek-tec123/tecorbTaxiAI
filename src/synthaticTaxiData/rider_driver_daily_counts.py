"""
Production-ready script to compute DAILY total counts
for riders or drivers (no H3, no hex).
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
from datetime import datetime, date
from typing import Dict, Iterable

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BATCH_SIZE = 10_000

ENTITY_CONFIG = {
    "riders": {
        "source_table": "riders",
        "target_table": "rider_daily_counts",
    },
    "drivers": {
        "source_table": "drivers",
        "target_table": "driver_daily_counts",
    },
}

# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------
def get_connection():
    return mysql_get_connection()


def stream_rows(cursor, batch_size: int = BATCH_SIZE) -> Iterable[Dict]:
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            yield row


# -----------------------------------------------------------------------------
# Schema
# -----------------------------------------------------------------------------
def create_daily_table(cursor, table_name: str) -> None:
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            report_date DATE PRIMARY KEY,
            total_count INT NOT NULL
        ) ENGINE=InnoDB;
        """
    )


# -----------------------------------------------------------------------------
# Fetch
# -----------------------------------------------------------------------------
def fetch_positions(cursor, source_table: str, target_date: date) -> None:
    cursor.execute(
        f"""
        SELECT activity_at
        FROM {source_table}
        WHERE DATE(activity_at) = %s
        """,
        (target_date,),
    )


# -----------------------------------------------------------------------------
# Compute
# -----------------------------------------------------------------------------
def compute_daily_count(cursor) -> int:
    total = 0
    for row in stream_rows(cursor):
        if row["activity_at"] is not None:
            total += 1
    return total


# -----------------------------------------------------------------------------
# Persist
# -----------------------------------------------------------------------------
def upsert_daily_count(
    cursor, table_name: str, report_date: date, total_count: int
) -> None:
    cursor.execute(
        f"""
        INSERT INTO {table_name} (report_date, total_count)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE total_count = VALUES(total_count)
        """,
        (report_date.isoformat(), total_count),
    )


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def process_entity(entity: str, target_date: date) -> None:
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unsupported entity: {entity}")

    cfg = ENTITY_CONFIG[entity]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        create_daily_table(cursor, cfg["target_table"])
        fetch_positions(cursor, cfg["source_table"], target_date)
        total_count = compute_daily_count(cursor)
        upsert_daily_count(cursor, cfg["target_table"], target_date, total_count)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main() -> None:
    TARGET_DATE_STR = "2025-11-17"
    target_date = datetime.strptime(TARGET_DATE_STR, "%Y-%m-%d").date()

    for entity in ("riders", "drivers"):
        process_entity(entity, target_date)
        print(f"Daily totals completed for {entity} on {TARGET_DATE_STR}")


if __name__ == "__main__":
    main()
