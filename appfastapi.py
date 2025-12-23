from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
MAP_DIR = os.path.join(BASE_DIR, "map_file")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from src.routes.registry import ROUTE_CONFIG

app = FastAPI(
    title="Taxi Simulation API",
    description="API wrapper for the taxi simulation project",
    version="1.0.0",
)

os.makedirs(MAP_DIR, exist_ok=True)
app.mount("/map_file", StaticFiles(directory=MAP_DIR), name="map_file")

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

@app.get("/routes", tags=["Meta"])
def list_routes():
    routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": sorted(route.methods),
                "name": route.name,
                "tags": route.tags,
            })
    return routes

# Register routers
API_PREFIX = "/api/v1"

for route in ROUTE_CONFIG:
    app.include_router(
        route["router"],
        prefix=f"{API_PREFIX}{route['prefix']}",
        tags=route["tags"],
    )
