import asyncio
import json
import logging
import aiohttp

from multi_armed_bandit import UCBBandit
from matcher import build_cost_matrix, match_and_analyze
from mapplot import plot_map
from osrm import osrm_route
from data_source import load_drivers_df, generate_riders_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RideMatching")


async def runmatcher():
    num_riders = int(input("Enter number of riders: "))

    # -------------------------------
    # Load data
    # -------------------------------
    drivers_df = load_drivers_df()
    riders_df = generate_riders_df(num_riders)

    drivers = drivers_df.rename(columns={"driver_id": "id"}).to_dict("records")
    riders = riders_df.rename(columns={"rider_id": "id"}).to_dict("records")

    # -------------------------------
    # Bandit setup
    # -------------------------------
    arms = [
        {"eta_w": 1.0, "dist_w": 0.0},
        {"eta_w": 0.7, "dist_w": 0.3},
        {"eta_w": 0.5, "dist_w": 0.5},
        {"eta_w": 0.3, "dist_w": 0.7},
    ]

    bandit = UCBBandit(arms)
    arm_idx = bandit.select_arm()
    arm = arms[arm_idx]

    logger.info("Selected arm %d → %s", arm_idx, arm)

    # -------------------------------
    # OSRM lookups
    # -------------------------------
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

    # -------------------------------
    # Matching
    # -------------------------------
    cost = build_cost_matrix(
        riders,
        drivers,
        eta_lookup,
        eta_w=arm["eta_w"],
        dist_w=arm["dist_w"]
    )

    matches, explanations, metrics = match_and_analyze(
        riders,
        drivers,
        cost,
        eta_lookup
    )

    # -------------------------------
    # Learning reward (bandit)
    # -------------------------------
    reward = -metrics["average_wait_time_sec"]
    bandit.update(arm_idx, reward)

    # -------------------------------
    # Map
    # -------------------------------
    map_file = plot_map(
        riders,
        drivers,
        matches,
        eta_lookup,
        route_lookup,
        "map.html"
    )

    # -------------------------------
    # Output (FINAL, COMPLETE)
    # -------------------------------
    output = {
        "message": "Ride matching completed successfully",
        "num_riders": num_riders,
        "result": {
            "matches": matches,
            "metrics": metrics,
            "average_reward_per_episode": round(bandit.average_reward, 3),
            "map_file": map_file
        }
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(runmatcher())
