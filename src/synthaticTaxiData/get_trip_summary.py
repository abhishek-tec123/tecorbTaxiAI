import mysql.connector
import json
from db_utils import get_conn

# -------------------------------
# Daily counts (JSON-ready)
# -------------------------------
def get_daily_driver_count(report_date):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT report_date, SUM(total_count) AS driver_total_count
        FROM driver_hourly_counts
        WHERE report_date = %s
        GROUP BY report_date
    """
    cursor.execute(query, (report_date,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return {
        "report_date": report_date,
        "driver_total_count": int(row["driver_total_count"]) if row else 0
    }


def get_daily_rider_count(report_date):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT report_date, SUM(total_count) AS rider_total_count
        FROM rider_hourly_counts
        WHERE report_date = %s
        GROUP BY report_date
    """
    cursor.execute(query, (report_date,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return {
        "report_date": report_date,
        "rider_total_count": int(row["rider_total_count"]) if row else 0
    }

# -------------------------------
# Hourly counts (JSON-ready)
# -------------------------------
def get_hourly_driver_counts(report_date):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT hour, total_count AS driver_total_count
        FROM driver_hourly_counts
        WHERE report_date = %s
        ORDER BY hour
    """
    cursor.execute(query, (report_date,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {
        "report_date": report_date,
        "hourly_driver_counts": [
            {"hour": int(row["hour"]), "driver_total_count": int(row["driver_total_count"])}
            for row in rows
        ]
    }


def get_hourly_rider_counts(report_date):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT hour, total_count AS rider_total_count
        FROM rider_hourly_counts
        WHERE report_date = %s
        ORDER BY hour
    """
    cursor.execute(query, (report_date,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {
        "report_date": report_date,
        "hourly_rider_counts": [
            {"hour": int(row["hour"]), "rider_total_count": int(row["rider_total_count"])}
            for row in rows
        ]
    }

# -------------------------------
# Trip summary (JSON-ready)
# -------------------------------
def get_daily_trip_summary(report_date):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    trip_query = """
        SELECT
            COUNT(*) AS total_trips,
            SUM(CASE WHEN cancellation_reason IS NULL THEN 1 ELSE 0 END) AS completed_trips,
            SUM(CASE WHEN cancellation_reason IS NOT NULL OR JSON_EXTRACT(meta, '$.cancellation_attempt') > 0 THEN 1 ELSE 0 END) AS cancelled_trips
        FROM trips
        WHERE DATE(start_at) = %s
    """
    cursor.execute(trip_query, (report_date,))
    result = cursor.fetchone()

    # Get daily driver/rider for missed rides
    daily_driver = get_daily_driver_count(report_date)["driver_total_count"]
    daily_rider = get_daily_rider_count(report_date)["rider_total_count"]
    missed_rides = max(daily_rider - daily_driver, 0)

    cursor.close()
    conn.close()

    return {
        "report_date": report_date,
        "total_trips": int(result["total_trips"]) if result else 0,
        "completed_trips": int(result["completed_trips"]) if result else 0,
        "cancelled_trips": int(result["cancelled_trips"]) if result else 0,
        "missed_rides": missed_rides
    }

# -------------------------------
# Main block
# -------------------------------
if __name__ == "__main__":
    report_date = "2025-07-07"

    daily_driver_json = get_daily_driver_count(report_date)
    daily_rider_json = get_daily_rider_count(report_date)
    # hourly_driver_json = get_hourly_driver_counts(report_date)
    # hourly_rider_json = get_hourly_rider_counts(report_date)
    trip_summary_json = get_daily_trip_summary(report_date)

    print("Daily Driver JSON:", json.dumps(daily_driver_json, indent=3))
    print("Daily Rider JSON:", json.dumps(daily_rider_json, indent=3))
    # print("Hourly Driver JSON:", json.dumps(hourly_driver_json, indent=3))
    # print("Hourly Rider JSON:", json.dumps(hourly_rider_json, indent=3))
    print("Trip Summary JSON:", json.dumps(trip_summary_json, indent=3))
