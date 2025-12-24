# from fastapi import APIRouter
# from pydantic import BaseModel
# from synthaticTaxiData.db_utils import get_conn

# router = APIRouter(prefix="/rider-driver", tags=["Driver & Rider Stats"])

# # -----------------------------
# # Request schema
# # -----------------------------
# class DateRequest(BaseModel):
#     report_date: str


# # ------------------------------------------------
# # DAILY DRIVER + RIDER
# # ------------------------------------------------
# @router.post("/daily")
# def get_daily_driver_rider(payload: DateRequest):
#     report_date = payload.report_date
#     conn = get_conn()
#     cursor = conn.cursor(dictionary=True)

#     # Driver daily
#     cursor.execute(
#         """
#         SELECT SUM(total_count) AS driver_total_count
#         FROM driver_hourly_counts
#         WHERE report_date = %s
#         """,
#         (report_date,)
#     )
#     driver_row = cursor.fetchone()

#     # Rider daily
#     cursor.execute(
#         """
#         SELECT SUM(total_count) AS rider_total_count
#         FROM rider_hourly_counts
#         WHERE report_date = %s
#         """,
#         (report_date,)
#     )
#     rider_row = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     return {
#         "report_date": report_date,
#         "daily_driver": int(driver_row["driver_total_count"] or 0),
#         "daily_rider": int(rider_row["rider_total_count"] or 0),
#     }


# # ------------------------------------------------
# # HOURLY DRIVER + RIDER
# # ------------------------------------------------
# @router.post("/hourly")
# def get_hourly_driver_rider(payload: DateRequest):
#     report_date = payload.report_date
#     conn = get_conn()
#     cursor = conn.cursor(dictionary=True)

#     # Driver hourly
#     cursor.execute(
#         """
#         SELECT hour, total_count AS driver_total_count
#         FROM driver_hourly_counts
#         WHERE report_date = %s
#         ORDER BY hour
#         """,
#         (report_date,)
#     )
#     driver_rows = cursor.fetchall()

#     # Rider hourly
#     cursor.execute(
#         """
#         SELECT hour, total_count AS rider_total_count
#         FROM rider_hourly_counts
#         WHERE report_date = %s
#         ORDER BY hour
#         """,
#         (report_date,)
#     )
#     rider_rows = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return {
#         "report_date": report_date,
#         "hourly_driver": [
#             {
#                 "hour": int(row["hour"]),
#                 "driver_total_count": int(row["driver_total_count"]),
#             }
#             for row in driver_rows
#         ],
#         "hourly_rider": [
#             {
#                 "hour": int(row["hour"]),
#                 "rider_total_count": int(row["rider_total_count"]),
#             }
#             for row in rider_rows
#         ],
#     }


from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from synthaticTaxiData.rider_driver_daily_counts import process_entity as process_daily_entity
from synthaticTaxiData.rider_driver_hourly_counts import process_entity as process_hourly_entity, compute_hourly_counts, get_connection

router = APIRouter(prefix="/rider-driver", tags=["Driver & Rider Stats"])

# -----------------------------
# Request schema
# -----------------------------
class DateRequest(BaseModel):
    report_date: str  # Format: "YYYY-MM-DD"


# ------------------------------------------------
# DAILY DRIVER + RIDER
# ------------------------------------------------
@router.post("/daily")
def get_daily_driver_rider(payload: DateRequest):
    report_date = datetime.strptime(payload.report_date, "%Y-%m-%d").date()

    # Compute daily totals using your script
    for entity in ("riders", "drivers"):
        process_daily_entity(entity, report_date)

    # Fetch the computed totals from the daily counts table
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT total_count AS driver_total_count FROM driver_daily_counts WHERE report_date = %s",
        (report_date,),
    )
    driver_row = cursor.fetchone()

    cursor.execute(
        "SELECT total_count AS rider_total_count FROM rider_daily_counts WHERE report_date = %s",
        (report_date,),
    )
    rider_row = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "report_date": report_date.isoformat(),
        "daily_driver": int(driver_row["driver_total_count"] or 0),
        "daily_rider": int(rider_row["rider_total_count"] or 0),
    }


# ------------------------------------------------
# HOURLY DRIVER + RIDER
# ------------------------------------------------
@router.post("/hourly")
def get_hourly_driver_rider(payload: DateRequest):
    report_date = datetime.strptime(payload.report_date, "%Y-%m-%d").date()

    # Compute hourly totals using your script
    for entity in ("riders", "drivers"):
        process_hourly_entity(entity, report_date)

    # Fetch the computed hourly totals
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT hour, total_count AS driver_total_count FROM driver_hourly_counts WHERE report_date = %s ORDER BY hour",
        (report_date,),
    )
    driver_rows = cursor.fetchall()

    cursor.execute(
        "SELECT hour, total_count AS rider_total_count FROM rider_hourly_counts WHERE report_date = %s ORDER BY hour",
        (report_date,),
    )
    rider_rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "report_date": report_date.isoformat(),
        "hourly_driver": [
            {"hour": int(row["hour"]), "driver_total_count": int(row["driver_total_count"])}
            for row in driver_rows
        ],
        "hourly_rider": [
            {"hour": int(row["hour"]), "rider_total_count": int(row["rider_total_count"])}
            for row in rider_rows
        ],
    }
