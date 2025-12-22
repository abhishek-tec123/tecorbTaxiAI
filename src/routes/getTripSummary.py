from fastapi import APIRouter
from pydantic import BaseModel
from synthaticTaxiData.db_utils import get_conn

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

    query = """
        SELECT
            COUNT(*) AS total_trips,
            SUM(
                CASE WHEN cancellation_reason IS NULL THEN 1 ELSE 0 END
            ) AS completed_trips,
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

    cursor.execute(query, (report_date,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "report_date": report_date,
        "total_trips": int(result["total_trips"] or 0),
        "completed_trips": int(result["completed_trips"] or 0),
        "cancelled_trips": int(result["cancelled_trips"] or 0),
    }
