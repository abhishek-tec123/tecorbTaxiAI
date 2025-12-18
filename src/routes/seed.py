from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date

from dataApp import seed

router = APIRouter(prefix="/seed", tags=["Seeding"])


class SeedRequest(BaseModel):
    drivers: int = Field(ge=1, default=5000)
    riders: int = Field(ge=1, default=5000)
    activity_date: date


@router.post("")
def seed_entities(payload: SeedRequest):
    try:
        seed(
            drivers=payload.drivers,
            riders=payload.riders,
            activity_date=payload.activity_date,
        )
        return {
            "message": "Drivers and riders seeded successfully",
            "drivers": payload.drivers,
            "riders": payload.riders,
            "date": payload.activity_date,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
