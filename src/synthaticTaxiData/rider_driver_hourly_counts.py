"""
Production-ready script to compute HOURLY total counts
for riders or drivers (no H3, no hex).
"""

from __future__ import annotations

from db_config import get_connection as mysql_get_connection
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, Iterable

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BATCH_SIZE = 10_000

ENTITY_CONFIG = {
    "riders": {
        "source_table": "riders",
        "target_table": "rider_hourly_counts",
    },
    "drivers": {
        "source_table": "drivers",
        "target_table": "driver_hourly_counts",
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
def create_hourly_table(cursor, table_name: str) -> None:
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            report_date DATE NOT NULL,
            hour TINYINT NOT NULL,
            total_count INT NOT NULL,
            PRIMARY KEY (report_date, hour)
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
def compute_hourly_counts(cursor) -> Dict[int, int]:
    hourly_counts: Dict[int, int] = defaultdict(int)

    for row in stream_rows(cursor):
        ts = row["activity_at"]
        if ts is None:
            continue
        hourly_counts[ts.hour] += 1

    return hourly_counts


# -----------------------------------------------------------------------------
# Persist
# -----------------------------------------------------------------------------
def upsert_hourly_counts(
    cursor,
    table_name: str,
    report_date: date,
    hourly_counts: Dict[int, int],
) -> None:
    for hour, count in hourly_counts.items():
        cursor.execute(
            f"""
            INSERT INTO {table_name} (report_date, hour, total_count)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE total_count = VALUES(total_count)
            """,
            (report_date.isoformat(), hour, count),
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
        create_hourly_table(cursor, cfg["target_table"])
        fetch_positions(cursor, cfg["source_table"], target_date)
        hourly_counts = compute_hourly_counts(cursor)
        upsert_hourly_counts(cursor, cfg["target_table"], target_date, hourly_counts)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
# def main() -> None:
#     TARGET_DATE_STR = "2025-11-17"
#     target_date = datetime.strptime(TARGET_DATE_STR, "%Y-%m-%d").date()

#     for entity in ("riders", "drivers"):
#         process_entity(entity, target_date)
#         print(f"Hourly totals completed for {entity} on {TARGET_DATE_STR}")

from datetime import datetime, timedelta, date


def main() -> None:
    START_DATE = date(2025, 7, 7)
    END_DATE = date(2025, 11, 17)

    current_date = START_DATE

    while current_date <= END_DATE:
        for entity in ("riders", "drivers"):
            process_entity(entity, current_date)
            print(
                f"Hourly totals completed for {entity} on {current_date.isoformat()}"
            )

        # move to next week
        current_date += timedelta(days=7)

if __name__ == "__main__":
    main()
