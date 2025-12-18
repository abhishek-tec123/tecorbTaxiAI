from fastapi import APIRouter, HTTPException
from datetime import date

from dataApp import init_db, seed, generate_trips, aggregate

router = APIRouter(prefix="/run-all", tags=["Orchestration"])


@router.post("")
def run_all(
    activity_date: date,
    drivers: int = 50,
    riders: int = 50,
    trips: int = 100,
):
    try:
        init_db()
        seed(
            drivers=drivers,
            riders=riders,
            activity_date=activity_date,
        )
        generate_trips(
            trip_date=activity_date,
            num_rides=trips,
            verbose=True,
        )
        aggregate(target_date=activity_date)

        return {
            "message": "Full taxi simulation completed",
            "date": activity_date,
            "drivers": drivers,
            "riders": riders,
            "trips": trips,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
