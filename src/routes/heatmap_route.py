# # src/routes/heatmap_route.py

# from fastapi import APIRouter
# from fastapi.responses import JSONResponse
# import os
# import shutil

# # Import your map generation function
# from synthaticTaxiData.rider_driver_heatmap import map_result  # adjust the import path if needed

# router = APIRouter()

# MAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../map_file")
# os.makedirs(MAP_DIR, exist_ok=True)


# @router.get("/generate_heatmap", tags=["Heatmap"])
# def generate_heatmap():
#     """
#     Generate rider/driver heatmap and return the map file path and hex stats.
#     """
#     result = map_result()

#     # Move the generated map HTML to the MAP_DIR if not already there
#     map_src = result["map_file"]
#     map_dest = os.path.join(MAP_DIR, os.path.basename(map_src))
#     if os.path.abspath(map_src) != os.path.abspath(map_dest):
#         shutil.move(map_src, map_dest)

#     return JSONResponse({
#         "map_url": f"/map_file/{os.path.basename(map_dest)}",
#         "hex_stats": result["hex_stats"]
#     })


# dynamc with date and time 

# src/routes/heatmap_route.py

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import os
import shutil
from pydantic import BaseModel

from synthaticTaxiData.rider_driver_heatmap import map_result_dynamic  # Updated to accept start/end timestamps

router = APIRouter()

MAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../map_file")
os.makedirs(MAP_DIR, exist_ok=True)


# -------------------------------
# Pydantic model for request body
# -------------------------------
class HeatmapRequest(BaseModel):
    start_ts: str  # e.g. "2025-07-07 07:00:00"
    end_ts: str    # e.g. "2025-07-07 08:00:00"


@router.post("/generate_heatmap", tags=["Heatmap"])
def generate_heatmap(req: HeatmapRequest):
    """
    Generate rider/driver heatmap for a given time window from JSON body.
    """
    result = map_result_dynamic(req.start_ts, req.end_ts)

    # Move the generated map HTML to MAP_DIR
    map_src = result["map_file"]
    map_dest = os.path.join(MAP_DIR, os.path.basename(map_src))
    if os.path.abspath(map_src) != os.path.abspath(map_dest):
        shutil.move(map_src, map_dest)

    # Full localhost URL
    local_url = f"http://127.0.0.1:8000/map_file/{os.path.basename(map_dest)}"

    return JSONResponse({
        "map_url": local_url,
        "hex_stats": result["hex_stats"]
    })