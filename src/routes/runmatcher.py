from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import logging

from matching.matcher import build_cost_matrix, match_and_analyze
from matching.mapplot import plot_map
from matching.osrm import osrm_route
from matching.data_source import load_drivers_df, generate_riders_df

router = APIRouter(prefix="/ride-matching", tags=["Ride Matching"])

logger = logging.getLogger("RideMatching")


class RideMatchingRequest(BaseModel):
    num_riders: int = Field(..., ge=1, description="Number of riders to generate")
    verbose: Optional[bool] = Field(default=False, description="Enable verbose logging")


async def runmatcher_async(num_riders: int):
    drivers_df = load_drivers_df()
    riders_df = generate_riders_df(num_riders)

    drivers = drivers_df.rename(columns={"driver_id": "id"}).to_dict("records")
    riders = riders_df.rename(columns={"rider_id": "id"}).to_dict("records")

    logger.info("Loaded %d drivers and %d riders", len(drivers), len(riders))

    eta_lookup = {}
    route_lookup = {}

    import aiohttp
    async with aiohttp.ClientSession() as session:
        for r in riders:
            eta_lookup[r["id"]] = {}
            for d in drivers:
                eta, dist, geom = await osrm_route(
                    session,
                    (d["lat"], d["lon"]),
                    (r["lat"], r["lon"])
                )
                eta_lookup[r["id"]][d["id"]] = {
                    "eta_sec": eta,
                    "distance_m": dist
                }
                route_lookup[(r["id"], d["id"])] = geom

    logger.info("OSRM routes computed")

    cost = build_cost_matrix(riders, drivers, eta_lookup)
    matches, explanations, metrics = match_and_analyze(
        riders, drivers, cost, eta_lookup
    )

    logger.info("Matching completed")

    map_file = plot_map(
        riders=riders,
        drivers=drivers,
        matches=matches,
        eta_lookup=eta_lookup,
        route_lookup=route_lookup,
        output_file="map.html"
    )

    logger.info("Map saved to %s", map_file)

    return {
        "matches": matches,
        "metrics": metrics,
        "map_file": "http://127.0.0.1:8000/map_file"
    }


@router.post("")
async def ride_matching(payload: RideMatchingRequest):
    try:
        result = await runmatcher_async(payload.num_riders)
        return {
            "message": "Ride matching completed successfully",
            "num_riders": payload.num_riders,
            "result": result
        }
    except Exception as e:
        logger.exception("Error in ride matching")
        raise HTTPException(status_code=500, detail=str(e))
