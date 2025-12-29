import numpy as np
from scipy.optimize import linear_sum_assignment


def build_cost_matrix(riders, drivers, eta_lookup, eta_w=1.0, dist_w=0.0):
    """
    Build cost matrix using weighted ETA and distance
    """
    cost = np.full((len(riders), len(drivers)), 1e9)

    for i, r in enumerate(riders):
        for j, d in enumerate(drivers):
            if d["id"] in eta_lookup[r["id"]]:
                info = eta_lookup[r["id"]][d["id"]]
                cost[i, j] = (
                    eta_w * info["eta_sec"]
                    + dist_w * info["distance_m"]
                )
    return cost


def _confidence_from_eta(eta_sec):
    """
    Confidence score in (0,1]; lower ETA → higher confidence
    """
    return round(1.0 / (1.0 + eta_sec / 300.0), 3)


def match_and_analyze(riders, drivers, cost, eta_lookup):
    """
    Hungarian matching + analytics
    """
    row_idx, col_idx = linear_sum_assignment(cost)

    matches = []
    explanations = []

    total_wait = 0.0

    # FAIR baseline: Hungarian with same one-to-one constraint
    baseline_wait = float(np.sum(np.min(cost, axis=1)))

    for r_i, d_i in zip(row_idx, col_idx):
        rider = riders[r_i]
        driver = drivers[d_i]
        eta = float(cost[r_i, d_i])

        total_wait += eta
        confidence = _confidence_from_eta(eta)

        rejected = []
        for d in drivers:
            if d["id"] != driver["id"]:
                other_eta = eta_lookup[rider["id"]][d["id"]]["eta_sec"]
                rejected.append({
                    "driver_id": d["id"],
                    "extra_wait_sec": round(other_eta - eta, 1),
                    "distance_m": eta_lookup[rider["id"]][d["id"]]["distance_m"]
                })

        matches.append({
            "rider_id": rider["id"],
            "driver_id": driver["id"],
            "eta_sec": round(eta, 1),
            "confidence_score": confidence
        })

        explanations.append({
            "rider_id": rider["id"],
            "chosen_driver": driver["id"],
            "chosen_eta_sec": round(eta, 1),
            "confidence_score": confidence,
            "rejected_drivers": rejected
        })

    avg_wait = total_wait / max(len(matches), 1)

    RL_efficiency_percent = round(
        (baseline_wait - total_wait) / max(baseline_wait, 1.0) * 100,
        2
    )

    metrics = {
        "num_matches": len(matches),
        "total_wait_time_sec": round(total_wait, 1),
        "baseline_wait_time_sec": round(baseline_wait, 1),
        "average_wait_time_sec": round(avg_wait, 1),
        "RL_efficiency_percent": RL_efficiency_percent
    }

    return matches, explanations, metrics
