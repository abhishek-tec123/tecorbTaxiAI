import numpy as np
from scipy.optimize import linear_sum_assignment

def build_cost_matrix(riders, drivers, eta_lookup):
    """
    Build a cost matrix of shape (num_riders, num_drivers) using OSRM ETA
    """
    cost = np.full((len(riders), len(drivers)), 1e9)
    for i, r in enumerate(riders):
        for j, d in enumerate(drivers):
            if d["id"] in eta_lookup[r["id"]]:
                cost[i, j] = eta_lookup[r["id"]][d["id"]]["eta_sec"]
    return cost


def match_and_analyze(riders, drivers, cost, eta_lookup):
    """
    Perform Hungarian matching and generate analytics
    Returns:
      matches: list of {rider_id, driver_id, eta_sec}
      explanations: list per rider, why chosen driver vs others
      metrics: total_wait_time_sec, baseline_wait_time_sec,
               average_wait_time_sec, wait_time_change_sec,
               wait_time_change_percent
    """

    row_idx, col_idx = linear_sum_assignment(cost)

    matches = []
    explanations = []
    total_wait = 0
    chosen_eta_list = []

    # Baseline: sum of each rider’s nearest driver ETA
    baseline_wait = sum(np.min(cost, axis=1))

    for r_i, d_i in zip(row_idx, col_idx):
        rider = riders[r_i]
        chosen_driver = drivers[d_i]
        chosen_eta = cost[r_i, d_i]
        total_wait += chosen_eta
        chosen_eta_list.append(chosen_eta)

        # Build explanation for rejected drivers
        rejected = []
        for d in drivers:
            if d["id"] != chosen_driver["id"]:
                delta = eta_lookup[rider["id"]][d["id"]]["eta_sec"] - chosen_eta
                rejected.append({
                    "driver_id": d["id"],
                    "extra_wait_sec": round(delta, 1),
                    "distance_m": eta_lookup[rider["id"]][d["id"]]["distance_m"]
                })

        explanations.append({
            "rider_id": rider["id"],
            "chosen_driver": chosen_driver["id"],
            "chosen_eta_sec": round(chosen_eta, 1),
            "rejected_drivers": rejected
        })

        matches.append({
            "rider_id": rider["id"],
            "driver_id": chosen_driver["id"],
            "eta_sec": round(chosen_eta, 1)
        })

    wait_time_change_sec = round(total_wait - baseline_wait, 1)
    wait_time_change_percent = round((total_wait - baseline_wait) / baseline_wait * 100, 2) if baseline_wait > 0 else 0

    metrics = {
        "total_wait_time_sec": round(total_wait, 1),
        "baseline_wait_time_sec": round(baseline_wait, 1),
        "average_wait_time_sec": round(total_wait / len(matches), 1),
        # "wait_time_change_sec": wait_time_change_sec,
        # "wait_time_change_percent": wait_time_change_percent
    }

    return matches, explanations, metrics
