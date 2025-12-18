from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from dataApp import init_db, seed, generate_trips, aggregate

router = APIRouter(prefix="/run-all", tags=["Orchestration"])

class RunAllRequest(BaseModel):
    activity_date: date
    drivers: int = 50
    riders: int = 50
    trips: int = 100


@router.post("")
def run_all(payload: RunAllRequest):
    try:
        init_db()
        seed(
            drivers=payload.drivers,
            riders=payload.riders,
            activity_date=payload.activity_date,
        )
        generate_trips(
            trip_date=payload.activity_date,
            num_rides=payload.trips,
            verbose=True,
        )
        aggregate(target_date=payload.activity_date)

        return {
            "message": "Full taxi simulation completed",
            "date": payload.activity_date,
            "drivers": payload.drivers,
            "riders": payload.riders,
            "trips": payload.trips,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
