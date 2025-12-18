from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date

from dataApp import generate_trips

router = APIRouter(prefix="/generate-trips", tags=["Trips"])


class GenerateTripsRequest(BaseModel):
    trip_date: date
    num_rides: int = Field(ge=1)
    batch_size: int = Field(default=1000, ge=1)
    progress_every: int = Field(default=100, ge=1)
    verbose: bool = False


@router.post("")
def generate_trips_route(payload: GenerateTripsRequest):
    try:
        generate_trips(
            trip_date=payload.trip_date,
            num_rides=payload.num_rides,
            batch_size=payload.batch_size,
            progress_every=payload.progress_every,
            verbose=payload.verbose,
        )
        return {
            "message": "Trips generated successfully",
            "trip_date": payload.trip_date,
            "num_rides": payload.num_rides,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
