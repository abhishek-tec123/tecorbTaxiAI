# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, Field
# from datetime import date

# from dataApp import seed

# router = APIRouter(prefix="/seed", tags=["Seeding"])


# class SeedRequest(BaseModel):
#     drivers: int = Field(ge=1, default=5000)
#     riders: int = Field(ge=1, default=5000)
#     activity_date: date


# @router.post("")
# def seed_entities(payload: SeedRequest):
#     try:
#         seed(
#             drivers=payload.drivers,
#             riders=payload.riders,
#             activity_date=payload.activity_date,
#         )
#         return {
#             "message": "Drivers and riders seeded successfully",
#             "drivers": payload.drivers,
#             "riders": payload.riders,
#             "date": payload.activity_date,
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date, timedelta
import random

from dataApp import seed  # your existing seed function

router = APIRouter(prefix="/seed", tags=["Seeding"])


# =====================================================
# CONFIG
# =====================================================

RIDER_MIN = 2700
RIDER_MAX = 3200

DRIVER_GAP_MIN = 100   # drivers less than riders
DRIVER_GAP_MAX = 200


# =====================================================
# REQUEST MODEL
# =====================================================

class SeedRequest(BaseModel):
    start_date: date
    end_date: date


# =====================================================
# HELPERS
# =====================================================

def monday_range(start: date, end: date):
    """Yield every Monday from start to end (inclusive)."""
    current = start
    while current <= end:
        if current.weekday() == 0:  # Monday
            yield current
        current += timedelta(days=1)


def generate_driver_rider_counts():
    riders = random.randint(RIDER_MIN, RIDER_MAX)
    gap = random.randint(DRIVER_GAP_MIN, DRIVER_GAP_MAX)
    drivers = max(1, riders - gap)
    return drivers, riders


# =====================================================
# ROUTE (SAME /seed)
# =====================================================

@router.post("")
def seed_entities(payload: SeedRequest):
    try:
        if payload.start_date > payload.end_date:
            raise ValueError("start_date must be before or equal to end_date")

        results = []

        for monday in monday_range(payload.start_date, payload.end_date):
            drivers, riders = generate_driver_rider_counts()

            seed(
                drivers=drivers,
                riders=riders,
                activity_date=monday,
            )

            results.append({
                "date": monday,
                "drivers": drivers,
                "riders": riders,
            })

        return {
            "message": "Seeding completed successfully",
            "weeks_seeded": len(results),
            "details": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
