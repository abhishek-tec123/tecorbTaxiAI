from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from synthaticTaxiData.db_utils import get_conn
from synthaticTaxiData.get_trip_summary import (
    get_daily_driver_count,
    get_daily_rider_count
)

router = APIRouter(
    prefix="/trip-summary-mondays",
    tags=["Trip Summary Mondays"]
)

# -----------------------------
# Request Model
# -----------------------------
class DateRequest(BaseModel):
    report_date: str  # e.g. "2025-08-18"

# -----------------------------
# Helper: Previous N Mondays
# -----------------------------
def previous_seven_mondays(report_date: date, count: int = 7):
    """
    Return previous `count` Mondays including the most recent Monday
    <= report_date (descending order).
    """
    days_to_monday = report_date.weekday()  # Monday = 0
    last_monday = report_date - timedelta(days=days_to_monday)

    return [last_monday - timedelta(weeks=i) for i in range(count)]

# -----------------------------
# Route: Trip Summary for Mondays
# -----------------------------
@router.post("/")
def get_trip_summary_mondays(payload: DateRequest):
    report_date = datetime.strptime(payload.report_date, "%Y-%m-%d").date()
    mondays = previous_seven_mondays(report_date, 7)

    result = {}

    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    for mon in mondays:
        trip_query = """
            SELECT
                COUNT(*) AS total_trips,

                -- Completed trips: no cancellation attempts
                SUM(
                    CASE
                        WHEN JSON_LENGTH(meta, '$.cancellation_attempts') IS NULL
                             OR JSON_LENGTH(meta, '$.cancellation_attempts') = 0
                        THEN 1 ELSE 0
                    END
                ) AS completed_trips,

                -- Cancelled trips: at least one cancellation attempt
                SUM(
                    CASE
                        WHEN JSON_LENGTH(meta, '$.cancellation_attempts') > 0
                        THEN 1 ELSE 0
                    END
                ) AS cancelled_trips
            FROM trips
            WHERE DATE(start_at) = %s
        """

        cursor.execute(trip_query, (mon,))
        trip_result = cursor.fetchone()

        daily_driver = get_daily_driver_count(mon)["driver_total_count"]
        daily_rider = get_daily_rider_count(mon)["rider_total_count"]

        missed_rides = max(daily_rider - daily_driver, 0)

        result[str(mon)] = {
            "completed_trips": int(trip_result["completed_trips"] or 0),
            "cancelled_trips": int(trip_result["cancelled_trips"] or 0),
            "missed_rides": missed_rides
        }

    cursor.close()
    conn.close()

    return {
        "trip_summary": result
    }
