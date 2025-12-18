import aiohttp
from typing import Tuple

OSRM_URL = "http://127.0.0.1:5002"

async def osrm_route(
    session: aiohttp.ClientSession,
    start: Tuple[float, float],
    end: Tuple[float, float]
):
    """
    Returns (duration_sec, distance_m, geometry)
    """
    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{start[1]},{start[0]};{end[1]},{end[0]}"
        "?overview=full&geometries=geojson"
    )

    async with session.get(url, timeout=10) as resp:
        data = await resp.json()
        route = data["routes"][0]
        return (
            route["duration"],
            route["distance"],
            route["geometry"]["coordinates"],
        )
