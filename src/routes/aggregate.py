from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date

from dataApp import aggregate

router = APIRouter(prefix="/aggregate", tags=["Aggregation"])


class AggregateRequest(BaseModel):
    target_date: date


@router.post("")
def aggregate_route(payload: AggregateRequest):
    try:
        aggregate(target_date=payload.target_date)
        return {
            "message": "Aggregations completed successfully",
            "date": payload.target_date,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
