from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sys

# Ensure we can import code from the `src` directory where all packages now live
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
MAP_DIR = os.path.join(BASE_DIR, "map_file")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from routes.init_db import router as init_db_router
from routes.seed import router as seed_router
from routes.generate_trips import router as generate_trips_router
from routes.aggregate import router as aggregate_router
from routes.run_all import router as run_all_router
from routes.runmatcher import router as ride_matching


app = FastAPI(
    title="Taxi Simulation API",
    description="API wrapper for the taxi simulation project",
    version="1.0.0",
)

# Mount static directory for generated maps/CSV files
if not os.path.exists(MAP_DIR):
    os.makedirs(MAP_DIR, exist_ok=True)

app.mount("/map_file", StaticFiles(directory=MAP_DIR), name="map_file")

# ----------------------------
# Health API (kept here)
# ----------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ----------------------------
# Register routers
# ----------------------------

app.include_router(init_db_router)
app.include_router(seed_router)
app.include_router(generate_trips_router)
app.include_router(aggregate_router)
app.include_router(ride_matching)

app.include_router(run_all_router)
