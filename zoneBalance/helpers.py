# helpers.py
import numpy as np
import json,uuid
from h3 import h3

def generate_dummy_driver_id():
    return uuid.uuid4().hex[:8]  # e.g. "1bd20e76"


def get_cross_group_adjacent_hexes(current_group_hexes, all_groups, hex_set, rider_counts, driver_counts):
    """
    Identify edge hexes in the current group and their adjacent hexes from other groups.
    
    Parameters:
    - current_group_hexes: list of hex IDs in the current group
    - all_groups: dict mapping group_id -> set of hex IDs
    - hex_set: set of all valid hex IDs
    - rider_counts: dict mapping hex_id -> rider count
    - driver_counts: dict mapping hex_id -> driver count
    
    Returns:
    - edge_hex_info: dict mapping edge_hex_id -> list of adjacent hexes from other groups
    - adjacent_hex_data: dict mapping adjacent_hex_id -> {'riders': int, 'drivers': int, 'group_id': int}
    - adjacent_hex_list: ordered list of adjacent hex IDs (for indexing)
    """
    current_group_set = set(current_group_hexes)
    edge_hex_info = {}  # edge_hex -> [adjacent_hexes from other groups]
    adjacent_hex_data = {}  # adjacent_hex -> {riders, drivers, group_id}
    adjacent_hex_set = set()
    
    # Find which group each hex belongs to
    hex_to_group = {}
    for gid, hexes in all_groups.items():
        for h in hexes:
            hex_to_group[h] = gid
    
    # For each hex in current group, check its neighbors
    for hex_id in current_group_hexes:
        neighbors = h3.k_ring(hex_id, 1)
        cross_group_neighbors = []
        
        for neighbor in neighbors:
            if neighbor not in hex_set or neighbor == hex_id:
                continue
            if neighbor not in current_group_set and neighbor in hex_to_group:
                # This neighbor is in a different group
                cross_group_neighbors.append(neighbor)
                adjacent_hex_set.add(neighbor)
                
                # Store data for this adjacent hex
                if neighbor not in adjacent_hex_data:
                    adjacent_hex_data[neighbor] = {
                        'riders': rider_counts.get(neighbor, 0),
                        'drivers': driver_counts.get(neighbor, 0),
                        'group_id': hex_to_group[neighbor]
                    }
        
        if cross_group_neighbors:
            edge_hex_info[hex_id] = cross_group_neighbors
    
    # Create ordered list of adjacent hexes for consistent indexing
    adjacent_hex_list = sorted(list(adjacent_hex_set))
    
    return edge_hex_info, adjacent_hex_data, adjacent_hex_list


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
                         episode_cumulative_reward=None, hex_ids=None, adjacent_hex_index_map=None):
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
    num_zones = len(agent_final_drivers)  # Current group size

    for idx, move in enumerate(agent_moves):
        f, t, num = move

        # Reward calculation - only process moves that affect current group
        # Skip if both zones are out of bounds (shouldn't happen after filtering, but safety check)
        if f >= num_zones and t >= num_zones:
            reward = 0.0
        else:
            prev_imbalance = np.sum(np.abs(temp_state))
            prev_perfect = np.sum(temp_state == 0)
            if num > 0 and f != t:
                # Only update drivers for zones within current group bounds
                if f < num_zones:
                    temp_drivers[f] -= num
                if t < num_zones:
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
            "driver_id": generate_dummy_driver_id(),
            "from_zone_id": int(f),
            "to_zone_id": int(t),
            "num_drivers": int(num),
            "reward": float(reward),
            "confidence_score": float(move_conf),
            "is_cross_group": False
        }
        
        # Add hex IDs if available, handling both current group and adjacent hexes
        from_hex_id = None
        to_hex_id = None
        
        # Check if from_zone is in current group or adjacent hex
        if hex_ids and f < len(hex_ids):
            from_hex_id = hex_ids[int(f)]
        elif adjacent_hex_index_map and f in adjacent_hex_index_map:
            from_hex_id = adjacent_hex_index_map[f]
            move_data["is_cross_group"] = True
        
        # Check if to_zone is in current group or adjacent hex
        if hex_ids and t < len(hex_ids):
            to_hex_id = hex_ids[int(t)]
        elif adjacent_hex_index_map and t in adjacent_hex_index_map:
            to_hex_id = adjacent_hex_index_map[t]
            move_data["is_cross_group"] = True
        
        if from_hex_id:
            move_data["from_hex"] = {
                "index": int(f),
                "hex_id": from_hex_id
            }
        if to_hex_id:
            move_data["to_hex"] = {
                "index": int(t),
                "hex_id": to_hex_id
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
                "num_drivers": int(num),
                "is_cross_group": False
            }
            # Add hex IDs if available, handling both current group and adjacent hexes
            from_hex_id = None
            to_hex_id = None
            
            # Check if from_zone is in current group or adjacent hex
            if hex_ids and f < len(hex_ids):
                from_hex_id = hex_ids[int(f)]
            elif adjacent_hex_index_map and f in adjacent_hex_index_map:
                from_hex_id = adjacent_hex_index_map[f]
                oracle_move_data["is_cross_group"] = True
            
            # Check if to_zone is in current group or adjacent hex
            if hex_ids and t < len(hex_ids):
                to_hex_id = hex_ids[int(t)]
            elif adjacent_hex_index_map and t in adjacent_hex_index_map:
                to_hex_id = adjacent_hex_index_map[t]
                oracle_move_data["is_cross_group"] = True
            
            if from_hex_id:
                oracle_move_data["from_hex"] = [int(f), from_hex_id]
            if to_hex_id:
                oracle_move_data["to_hex"] = [int(t), to_hex_id]
            
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
            "metrics": {
                "relocation_success_rate": float(relocation_success_rate) if relocation_success_rate is not None else None,
                "average_reward_per_episode": float(avg_reward_per_episode) if avg_reward_per_episode is not None else 0.0,
                "zone_confidence_scores": zone_conf_dict
            }
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
