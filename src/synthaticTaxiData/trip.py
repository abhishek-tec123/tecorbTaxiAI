import uuid
import random
import json
from datetime import datetime, date

from db_utils import (
    get_conn,
    fetch_one_rider,
    fetch_driver_within_distance,
    insert_trip,
    update_trip_fields,
    log_match_event,
    update_driver_location
)
from helpers import haversine_km, generate_trip_datetime, build_trip_blueprint

# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------
MAX_PICKUP_DISTANCE_KM = 5
CANCELLATION_PROBABILITY = 0.20
CANCELLATION_REASONS = [
    "waiting time too long",
    "wrong pickup location",
    "passenger no-show"
]

# ---------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------
def now_iso():
    return datetime.utcnow().isoformat()

def compute_response_time_ms(blueprint):
    return int(
        (blueprint["matched_at"] - blueprint["requested_at"]).total_seconds() * 1000
    )

def simulate_cancellation():
    if random.random() < CANCELLATION_PROBABILITY:
        return random.choice(CANCELLATION_REASONS)
    return None

# ---------------------------------------------------------
# Matching logic
# ---------------------------------------------------------
def attempt_match(
    conn,
    trip_id,
    rider_id,
    pickup_lat,
    pickup_lon,
    blueprint,
    matcher_version
):
    """
    Attempts to match a driver.
    Returns (success, driver_id, pickup_distance_km, cancellation_reason)
    """
    driver = fetch_driver_within_distance(
        conn, pickup_lat, pickup_lon, MAX_PICKUP_DISTANCE_KM
    )
    if not driver:
        return False, None, None, "no drivers available"

    driver_id = driver["driver_id"]
    pickup_distance_km = round(
        haversine_km(driver["lat"], driver["lon"], pickup_lat, pickup_lon), 2
    )

    cancellation_reason = simulate_cancellation()
    response_time_ms = compute_response_time_ms(blueprint)

    if cancellation_reason:
        log_match_event(
            conn,
            trip_id=trip_id,
            driver_id=driver_id,
            rider_id=rider_id,
            distance_km=blueprint["distance_km"],
            match_status="cancelled",
            matcher_version=matcher_version,
            reward_estimate=blueprint["match_quality"],
            response_time_ms=response_time_ms,
            commit=False
        )
        return False, driver_id, pickup_distance_km, cancellation_reason

    # Driver accepts
    update_driver_location(
        conn,
        driver_id,
        blueprint["drop_lat"],
        blueprint["drop_lon"],
        commit=False
    )

    log_match_event(
        conn,
        trip_id=trip_id,
        driver_id=driver_id,
        rider_id=rider_id,
        distance_km=blueprint["distance_km"],
        match_status="completed",
        matcher_version=matcher_version,
        reward_estimate=blueprint["match_quality"],
        response_time_ms=response_time_ms,
        commit=False
    )

    return True, driver_id, pickup_distance_km, None

# ---------------------------------------------------------
# Trip lifecycle
# ---------------------------------------------------------
def create_test_trip(
    forced_timestamp=None,
    max_rematch_attempts=2,
    matcher_version="baseline-v1",
    retry_on_cancel=True,
    conn=None,
    commit=True,
    verbose=True
):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()

    try:
        rider = fetch_one_rider(conn)
        rider_id = rider["rider_id"]
        pickup_lat = float(rider["lat"])
        pickup_lon = float(rider["lon"])

        blueprint = build_trip_blueprint(
            pickup_lat,
            pickup_lon,
            forced_timestamp=forced_timestamp
        )

        trip_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        insert_trip(
            conn,
            (
                trip_id,
                request_id,
                rider_id,
                None,
                "pending",
                blueprint["requested_at"],
                blueprint["matched_at"],
                blueprint["start_at"],
                blueprint["end_at"],
                pickup_lat,
                pickup_lon,
                blueprint["drop_lat"],
                blueprint["drop_lon"],
                None,
                blueprint["distance_km"],
                blueprint["ride_duration_min"],
                blueprint["total_wait"],
                None,
                None,
                blueprint["match_quality"],
                datetime.utcnow(),
                json.dumps({"cancellation_attempts": []})
            ),
            commit=False
        )

        cancellations = []
        success = False
        driver_id = None
        pickup_distance_km = None
        final_reason = None

        for attempt in range(1, max_rematch_attempts + 2):
            success, driver_id, pickup_distance_km, reason = attempt_match(
                conn,
                trip_id,
                rider_id,
                pickup_lat,
                pickup_lon,
                blueprint,
                matcher_version
            )

            if success:
                break

            cancellations.append({
                "attempt": attempt,
                "driver_id": driver_id,
                "reason": reason,
                "timestamp": now_iso()
            })
            final_reason = reason

            if not retry_on_cancel or attempt > max_rematch_attempts:
                break

        update_trip_fields(
            conn,
            trip_id,
            driver_id=driver_id,
            status="completed" if success else "cancelled",
            pickup_distance_km=pickup_distance_km if success else None,
            ride_distance_km=blueprint["distance_km"] if success else None,
            ride_duration_min=blueprint["ride_duration_min"] if success else None,
            wait_time_min=blueprint["total_wait"],
            fare=blueprint["fare"] if success else None,
            cancellation_reason=None if success else final_reason,
            meta=json.dumps({"cancellation_attempts": cancellations}),
            commit=False
        )

        if commit:
            conn.commit()

        if verbose:
            print(
                f"Trip {trip_id[:6]} | {blueprint['requested_at']} "
                f"status={'completed' if success else 'cancelled'} "
                f"cancels={len(cancellations)}"
            )

    finally:
        if own_conn:
            conn.close()

# ---------------------------------------------------------
# Daily generator
# ---------------------------------------------------------
def create_trips_for_date(
    target_date: date,
    num_rides: int,
    batch_size: int = 1000,
    progress_every: int = 100,
    verbose: bool = False
):
    print(
        f"\nGenerating {num_rides} trips for {target_date} "
        f"(batch_size={batch_size})"
    )

    timestamps = generate_trip_datetime(target_date, num_rides)
    conn = get_conn()

    try:
        for i, ts in enumerate(timestamps, 1):
            create_test_trip(
                forced_timestamp=ts,
                conn=conn,
                commit=False,
                verbose=verbose
            )

            if i % batch_size == 0:
                conn.commit()
                print(f"Committed {i}/{num_rides}")

            if verbose or i % progress_every == 0:
                print(f"[{i}/{num_rides}] inserted @ {ts}")

        conn.commit()
    finally:
        conn.close()

# # ---------------------------------------------------------
# # Run
# # ---------------------------------------------------------
# if __name__ == "__main__":
#     create_trips_for_date(date(2025, 11, 3), 2900)
#     # create_trips_for_date(date(2025, 11, 10), 2840)
#     # create_trips_for_date(date(2025, 11, 17), 2730)
#     # create_trips_for_date(date(2025, 10, 27), 2860)
#     # create_trips_for_date(date(2025, 9, 29), 3210)