# src/routes/registry.py

from src.routes.init_db import router as init_db_router
from src.routes.seed import router as seed_router
from src.routes.generate_trips import router as generate_trips_router
from src.routes.aggregate import router as aggregate_router
from src.routes.run_all import router as run_all_router
from src.routes.runmatcher import router as ride_matching_router
from src.routes.getDailyHrly_rider_drvr import router as rider_driver_router
from src.routes.getTripSummary import router as trip_summary_router

from src.routes.generate_trips2 import router as generate_trips_router2
from src.routes.heatmap_route import router as heatmap_router
from src.routes.sevenMon_rider_driver import router as trip_summary_mondays_router  # new Mondays route

from src.routes.train_group import router as train_group_route

ROUTE_CONFIG = [
    {
        "router": init_db_router,
        "prefix": "/db",
        "tags": ["Database"],
    },
    {
        "router": seed_router,
        "prefix": "/seed",
        "tags": ["Database"],
    },
    {
        "router": generate_trips_router,
        "prefix": "/trips",
        "tags": ["Simulation"],
    },
    {
        "router": aggregate_router,
        "prefix": "/aggregate",
        "tags": ["Analytics"],
    },
    {
        "router": run_all_router,
        "prefix": "/run",
        "tags": ["Orchestration"],
    },
    {
        "router": ride_matching_router,
        "prefix": "/match",
        "tags": ["Matching"],
    },
    {
        "router": rider_driver_router,
        "prefix": "/stats",
        "tags": ["Analytics"],
    },
    {
        "router": trip_summary_router,
        "prefix": "/summary",
        "tags": ["Analytics"],
    },
    {
        "router": generate_trips_router2,
        "prefix": "/trips",
        "tags": ["Trips with multiple date"],
    },
    {
        "router": heatmap_router,
        "prefix": "/heatmap",
        "tags": ["Heatmap"]
    },
        # New route for previous 7 Mondays
    {
        "router": trip_summary_mondays_router,
        "prefix": "/trip-summary-mondays",
        "tags": ["Trip Summary Mondays"]
    },

    {
    "router": train_group_route,
    "prefix": "/train",
    "tags": ["Training", "RL"],
    }
]
