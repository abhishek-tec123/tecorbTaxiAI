import asyncio
import json
import logging
import aiohttp

from matcher import build_cost_matrix, match_and_analyze
from mapplot import plot_map
from osrm import osrm_route
from data_source import load_drivers_df, generate_riders_df

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RideMatching")

# =====================================================
# MAIN
# =====================================================

async def runmatcher():
    num_riders = int(input("Enter number of riders: "))

    # -------------------------------------------------
    # LOAD DATA
    # -------------------------------------------------
    drivers_df = load_drivers_df()
    riders_df = generate_riders_df(num_riders)

    drivers = drivers_df.rename(columns={"driver_id": "id"}).to_dict("records")
    riders = riders_df.rename(columns={"rider_id": "id"}).to_dict("records")

    logger.info("Loaded %d drivers and %d riders", len(drivers), len(riders))

    # -------------------------------------------------
    # OSRM ETA LOOKUPS
    # -------------------------------------------------
    eta_lookup = {}
    route_lookup = {}

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

    # -------------------------------------------------
    # MATCHING
    # -------------------------------------------------
    cost = build_cost_matrix(riders, drivers, eta_lookup)

    matches, explanations, metrics = match_and_analyze(
        riders,
        drivers,
        cost,
        eta_lookup
    )

    logger.info("Matching completed")

    # -------------------------------------------------
    # MAP
    # -------------------------------------------------
    map_file = plot_map(
        riders=riders,
        drivers=drivers,
        matches=matches,
        eta_lookup=eta_lookup,
        route_lookup=route_lookup,
        output_file="map.html"
    )

    logger.info("Map saved to %s", map_file)

    # -------------------------------------------------
    # OUTPUT
    # -------------------------------------------------
    output = {
        "matches": matches,
        "metrics": metrics,
        "map_file": map_file
    }

    print(json.dumps(output, indent=2))


# # =====================================================
# # RUN
# # =====================================================

# if __name__ == "__main__":
#     asyncio.run(runmatcher())
