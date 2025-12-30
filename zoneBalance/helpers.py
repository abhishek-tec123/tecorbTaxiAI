# helpers.py
import numpy as np
import json

def performance_score(final_balance, riders, weight_perfect=0.7):
    """
    Calculate performance score of a final driver distribution.
    """
    final_balance = np.array(final_balance)
    riders = np.array(riders)
    num_zones = len(final_balance)
    perfect_fraction = np.sum(final_balance == 0) / num_zones
    normalized_imbalance = np.sum(np.abs(final_balance)) / np.sum(riders)
    score = weight_perfect * perfect_fraction + (1 - weight_perfect) * (1 - normalized_imbalance)
    return score, perfect_fraction, normalized_imbalance


def generate_json_output(agent_state, agent_final_drivers, agent_final_riders, agent_moves,
                         oracle_state, oracle_final_drivers, oracle_final_riders, oracle_moves,
                         agent_score, oracle_score, riders, drivers,
                         relocation_success_rate=0.0, zone_confidence_scores=None,
                         move_confidence_scores=None, avg_reward_per_episode=0.0,
                         episode_cumulative_reward=None, hex_ids=None):
    """
    Generate JSON output with:
      - Zone-level details
      - Agent and oracle moves
      - Reward per agent move
      - RL accuracy metrics
    """
    num_zones = len(agent_state)
    balanced_zones_agent = np.sum(agent_state == 0)
    
    # Handle None oracle values
    has_oracle = oracle_state is not None
    if has_oracle:
        oracle_state = np.array(oracle_state)
        balanced_zones_oracle = np.sum(oracle_state == 0)
    else:
        balanced_zones_oracle = 0
    
    zones = []

    # RL accuracy metrics (only if oracle is available)
    if has_oracle:
        perfect_zones_match = np.sum((agent_state == 0) & (oracle_state == 0))
        perfect_zones_oracle = np.sum(oracle_state == 0)
        rl_accuracy_perfect = perfect_zones_match / perfect_zones_oracle if perfect_zones_oracle > 0 else 0.0

        state_diff = np.abs(agent_state - oracle_state)
        max_possible_diff = np.sum(np.abs(oracle_state)) if np.sum(np.abs(oracle_state)) > 0 else 1
        rl_accuracy_state = 1.0 - (np.sum(state_diff) / max_possible_diff) if max_possible_diff > 0 else 0.0
        rl_accuracy_state = max(0.0, min(1.0, rl_accuracy_state))
        rl_accuracy = 0.6 * rl_accuracy_perfect + 0.4 * rl_accuracy_state
    else:
        rl_accuracy = 0.0
        rl_accuracy_perfect = 0.0
        rl_accuracy_state = 0.0

    # ---------------- Zone-level details ----------------
    for zone_id in range(num_zones):
        zone_data = {
            "zone_id": int(zone_id),
            "initial_riders": int(agent_final_riders[zone_id]),
            "initial_drivers": int(drivers[zone_id]),
            "final_drivers_agent": int(agent_final_drivers[zone_id]),
            "final_balance_agent": int(agent_state[zone_id]),
            "is_balanced_agent": bool(agent_state[zone_id] == 0),
            "balance_status": "balanced" if agent_state[zone_id] == 0 else ("surplus" if agent_state[zone_id] < 0 else "deficit"),
            "imbalance_magnitude": int(abs(agent_state[zone_id]))
        }
        if has_oracle:
            zone_data["final_balance_oracle"] = int(oracle_state[zone_id])
            zone_data["is_balanced_oracle"] = bool(oracle_state[zone_id] == 0)
        zones.append(zone_data)

    # ---------------- Agent moves with reward and confidence scores ----------------
    dispatch_moves_agent = []
    temp_drivers = agent_final_drivers.copy()
    temp_state = agent_final_riders - temp_drivers

    for idx, move in enumerate(agent_moves):
        f, t, num = move

        # Reward calculation
        prev_imbalance = np.sum(np.abs(temp_state))
        prev_perfect = np.sum(temp_state == 0)
        if num > 0 and f != t:
            temp_drivers[f] -= num
            temp_drivers[t] += num
            next_state = agent_final_riders - temp_drivers
            current_imbalance = np.sum(np.abs(next_state))
            current_perfect = np.sum(next_state == 0)
            reward = float((prev_imbalance - current_imbalance) * 3.0 + 5.0 * (current_perfect - prev_perfect))
            temp_state = next_state.copy()
        else:
            reward = 0.0

        # Get confidence score for this move if available
        move_conf = 0.0
        if move_confidence_scores and idx < len(move_confidence_scores):
            move_conf = move_confidence_scores[idx].get("confidence_score", 0.0)

        move_data = {
            "from_zone_id": int(f),
            "to_zone_id": int(t),
            "num_drivers": int(num),
            "reward": float(reward),
            "confidence_score": float(move_conf)
        }
        
        # Add hex IDs if available
        if hex_ids and len(hex_ids) > max(f, t):
            move_data["from_hex"] = {
                "index": int(f),
                "hex_id": hex_ids[int(f)]
            }
            move_data["to_hex"] = {
                "index": int(t),
                "hex_id": hex_ids[int(t)]
            }

        dispatch_moves_agent.append(move_data)

    # ---------------- Oracle moves ----------------
    dispatch_moves_oracle = []
    if oracle_moves is not None:
        for m in oracle_moves:
            f, t, num = m[0], m[1], m[2]
            oracle_move_data = {
                "from_zone_id": int(f),
                "to_zone_id": int(t),
                "num_drivers": int(num)
            }
            # Add hex IDs if available
            if hex_ids and len(hex_ids) > max(f, t):
                oracle_move_data["from_hex"] = [int(f), hex_ids[int(f)]]
                oracle_move_data["to_hex"] = [int(t), hex_ids[int(t)]]
            dispatch_moves_oracle.append(oracle_move_data)

    # Prepare zone confidence scores
    zone_conf_dict = {}
    if zone_confidence_scores:
        for zone_id in range(min(len(zone_confidence_scores), num_zones)):
            zone_conf_dict[int(zone_id)] = float(zone_confidence_scores[zone_id])
    
    return {
        "summary": {
            "total_zones": int(num_zones),
            "agent_performance": {
                "balanced_zones": int(balanced_zones_agent),
                "unbalanced_zones": num_zones - int(balanced_zones_agent),
                "combined_score": float(agent_score) if agent_score is not None else None,
                "total_moves": len(agent_moves)
            },
            # "oracle_performance": {
            #     "balanced_zones": int(balanced_zones_oracle),
            #     "unbalanced_zones": num_zones - int(balanced_zones_oracle),
            #     "combined_score": float(oracle_score) if oracle_score is not None else None,
            #     "total_moves": len(oracle_moves) if oracle_moves is not None else 0
            # },
            "rl_accuracy": {
                "overall_accuracy": float(rl_accuracy),
                "perfect_zones_accuracy": float(rl_accuracy_perfect),
                # "state_similarity_accuracy": float(rl_accuracy_state)
            },
            # "metrics": {
            #     "relocation_success_rate": float(relocation_success_rate) if relocation_success_rate is not None else None,
            #     "average_reward_per_episode": float(avg_reward_per_episode) if avg_reward_per_episode is not None else 0.0,
            #     "zone_confidence_scores": zone_conf_dict
            # }
        },
        # "zones": zones,
        "dispatch_moves": {
            "agent_moves": dispatch_moves_agent,
            # "oracle_moves": dispatch_moves_oracle
        },
        "training_performance": {
            "episode_cumulative_reward": episode_cumulative_reward if episode_cumulative_reward else {}
        }
    }
