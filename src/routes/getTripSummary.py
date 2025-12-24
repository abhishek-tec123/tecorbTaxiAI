from fastapi import APIRouter
from pydantic import BaseModel
from synthaticTaxiData.db_utils import get_conn
from synthaticTaxiData.get_trip_summary import get_daily_driver_count, get_daily_rider_count  # import your functions

router = APIRouter(
    prefix="/trip-summary",
    tags=["Trip Summary"]
)

# -----------------------------
# Request schema
# -----------------------------
class DateRequest(BaseModel):
    report_date: str


# -----------------------------
# Trip Summary Route
# -----------------------------
@router.post("/")
def get_trip_summary(payload: DateRequest):
    report_date = payload.report_date
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    # Compute trip summary
    trip_query = """
        SELECT
            COUNT(*) AS total_trips,
            SUM(CASE WHEN cancellation_reason IS NULL THEN 1 ELSE 0 END) AS completed_trips,
            SUM(
                CASE
                    WHEN cancellation_reason IS NOT NULL
                         OR JSON_EXTRACT(meta, '$.cancellation_attempt') > 0
                    THEN 1 ELSE 0
                END
            ) AS cancelled_trips
        FROM trips
        WHERE DATE(start_at) = %s
    """
    cursor.execute(trip_query, (report_date,))
    trip_result = cursor.fetchone()
    cursor.close()
    conn.close()

    # Get daily driver and rider counts
    daily_driver = get_daily_driver_count(report_date)["driver_total_count"]
    daily_rider = get_daily_rider_count(report_date)["rider_total_count"]
    missed_rides = max(daily_rider - daily_driver, 0)
    total_trips = int(trip_result["total_trips"] or 0)

    # Construct response
    response = {
        "trip_summary": {
            "completed_trips": int(trip_result["completed_trips"] or 0),
            "cancelled_trips": int(trip_result["cancelled_trips"] or 0),
            "missed_rides": missed_rides
        },
        "daily_counts": {
            "total_driver": daily_driver,
            "total_rider": daily_rider,
            "total_trips": total_trips
        }
    }

    return response
