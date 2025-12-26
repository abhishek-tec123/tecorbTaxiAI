from pydantic import BaseModel
from datetime import date
from fastapi import APIRouter, Query
import random
from synthaticTaxiData.trip import create_trips_for_date  # adjust import

router = APIRouter()

class TripRequest(BaseModel):
    dates: list[date]

@router.post("/generate-trips2")
def generate_trips(
    request: TripRequest,
    min_trips: int = Query(200, ge=1),
    max_trips: int = Query(250, ge=1),
):
    results = []

    for trip_date in request.dates:
        num_trips = random.randint(min_trips, max_trips)
        create_trips_for_date(trip_date, num_trips)
        results.append({
            "date": trip_date,
            "trips_created": num_trips
        })

    return {
        "status": "success",
        "results": results
    }
