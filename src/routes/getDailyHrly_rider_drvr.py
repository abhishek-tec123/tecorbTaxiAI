from fastapi import APIRouter
from pydantic import BaseModel
from synthaticTaxiData.db_utils import get_conn

router = APIRouter(prefix="/rider-driver", tags=["Driver & Rider Stats"])

# -----------------------------
# Request schema
# -----------------------------
class DateRequest(BaseModel):
    report_date: str


# ------------------------------------------------
# DAILY DRIVER + RIDER
# ------------------------------------------------
@router.post("/daily")
def get_daily_driver_rider(payload: DateRequest):
    report_date = payload.report_date
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    # Driver daily
    cursor.execute(
        """
        SELECT SUM(total_count) AS driver_total_count
        FROM driver_hourly_counts
        WHERE report_date = %s
        """,
        (report_date,)
    )
    driver_row = cursor.fetchone()

    # Rider daily
    cursor.execute(
        """
        SELECT SUM(total_count) AS rider_total_count
        FROM rider_hourly_counts
        WHERE report_date = %s
        """,
        (report_date,)
    )
    rider_row = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "report_date": report_date,
        "daily_driver": int(driver_row["driver_total_count"] or 0),
        "daily_rider": int(rider_row["rider_total_count"] or 0),
    }


# ------------------------------------------------
# HOURLY DRIVER + RIDER
# ------------------------------------------------
@router.post("/hourly")
def get_hourly_driver_rider(payload: DateRequest):
    report_date = payload.report_date
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)

    # Driver hourly
    cursor.execute(
        """
        SELECT hour, total_count AS driver_total_count
        FROM driver_hourly_counts
        WHERE report_date = %s
        ORDER BY hour
        """,
        (report_date,)
    )
    driver_rows = cursor.fetchall()

    # Rider hourly
    cursor.execute(
        """
        SELECT hour, total_count AS rider_total_count
        FROM rider_hourly_counts
        WHERE report_date = %s
        ORDER BY hour
        """,
        (report_date,)
    )
    rider_rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "report_date": report_date,
        "hourly_driver": [
            {
                "hour": int(row["hour"]),
                "driver_total_count": int(row["driver_total_count"]),
            }
            for row in driver_rows
        ],
        "hourly_rider": [
            {
                "hour": int(row["hour"]),
                "rider_total_count": int(row["rider_total_count"]),
            }
            for row in rider_rows
        ],
    }
