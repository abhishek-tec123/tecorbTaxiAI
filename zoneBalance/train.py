# train.py
import numpy as np
import json
from zoneBalance.dqn import DQNAgent
from zoneBalance.oracle import Oracle
from zoneBalance.helpers import performance_score, generate_json_output, get_cross_group_adjacent_hexes

# import sys
# import os

# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# sys.path.append(PROJECT_ROOT)


class MultiZoneEnv:
    def __init__(self, riders, drivers, max_moves=50, adjacent_hexes_data=None, current_group_size=None):
        """
        Parameters:
        - riders: list of rider counts for current group hexes
        - drivers: list of driver counts for current group hexes
        - max_moves: maximum number of moves allowed
        - adjacent_hexes_data: dict mapping adjacent_hex_id -> {'riders': int, 'drivers': int}
        - current_group_size: number of hexes in the current group (to distinguish from adjacent hexes)
        """
        self.riders = np.array(riders, dtype=int)
        self.initial_drivers = np.array(drivers, dtype=int)
        self.max_moves = max_moves
        self.current_group_size = current_group_size if current_group_size is not None else len(riders)
        
        # Handle adjacent hexes from other groups
        self.adjacent_hexes_data = adjacent_hexes_data or {}
        self.adjacent_hex_list = sorted(list(self.adjacent_hexes_data.keys())) if self.adjacent_hexes_data else []
        self.num_adjacent = len(self.adjacent_hex_list)
        
        # Extended state includes both current group and adjacent hexes
        if self.num_adjacent > 0:
            adjacent_riders = [self.adjacent_hexes_data[h]['riders'] for h in self.adjacent_hex_list]
            adjacent_drivers = [self.adjacent_hexes_data[h]['drivers'] for h in self.adjacent_hex_list]
            self.riders = np.concatenate([self.riders, np.array(adjacent_riders, dtype=int)])
            self.initial_drivers = np.concatenate([self.initial_drivers, np.array(adjacent_drivers, dtype=int)])
        
        self.num_zones = len(self.riders)
        self.reset()

    def reset(self):
        self.drivers = self.initial_drivers.copy()
        self.state = self.riders - self.drivers
        self.moves_done = 0
        self.cumulative_reward = 0.0
        self.prev_imbalance = np.sum(np.abs(self.state[:self.current_group_size]))  # Only count current group
        self.prev_perfect = np.sum(self.state[:self.current_group_size] == 0)
        self.dispatch_summary = []
        return self.state.copy()

    def step(self, action):
        from_z, to_z, num_drivers = action
        num_drivers = min(int(num_drivers), int(self.drivers[from_z]))
        if num_drivers > 0 and from_z != to_z:
            self.drivers[from_z] -= num_drivers
            self.drivers[to_z] += num_drivers
            self.moves_done += 1
            # Store move with indication if it's cross-group
            is_cross_group = (from_z >= self.current_group_size) or (to_z >= self.current_group_size)
            self.dispatch_summary.append((from_z, to_z, int(num_drivers), is_cross_group))
        self.state = self.riders - self.drivers
        reward = self.calculate_reward()
        self.cumulative_reward += reward
        done = self.moves_done >= self.max_moves
        return self.state.copy(), reward, done

    def calculate_reward(self):
        # Only calculate reward based on current group balance (not adjacent hexes)
        current_group_state = self.state[:self.current_group_size]
        current_imbalance = np.sum(np.abs(current_group_state))
        current_perfect = np.sum(current_group_state == 0)
        reward = (self.prev_imbalance - current_imbalance) * 3.0
        reward += 5.0 * (current_perfect - self.prev_perfect)
        self.prev_imbalance = current_imbalance
        self.prev_perfect = current_perfect
        return float(reward)

def train_single_group(group_json, group_id, all_groups=None, hex_set=None, rider_counts=None, driver_counts=None):
    """
    Train for a single group with support for cross-group balancing.
    
    Parameters:
      - group_json: JSON output from groups_to_json()
      - group_id: integer 1, 2, 3, or 4 representing the group
      - all_groups: dict mapping group_id -> set of hex IDs (for cross-group adjacency)
      - hex_set: set of all valid hex IDs
      - rider_counts: dict mapping hex_id -> rider count
      - driver_counts: dict mapping hex_id -> driver count
    """
    gid = f"group_{group_id}"
    
    # Extract per-hex riders and drivers for this group
    hexes_info = group_json[gid]["hexes"]
    
    # Each hex is treated as a separate zone
    riders = [h["riders"] for h in hexes_info]
    drivers = [h["drivers"] for h in hexes_info]
    hex_ids = [h["hex_id"] for h in hexes_info]  # Extract hex IDs for mapping
    current_group_hexes = [h["hex_id"] for h in hexes_info]
    
    # Get cross-group adjacent hexes if information is provided
    adjacent_hexes_data = None
    adjacent_hex_list = []
    if all_groups is not None and hex_set is not None and rider_counts is not None and driver_counts is not None:
        edge_hex_info, adjacent_hex_data, adjacent_hex_list = get_cross_group_adjacent_hexes(
            current_group_hexes, all_groups, hex_set, rider_counts, driver_counts
        )
        if adjacent_hex_list:
            adjacent_hexes_data = adjacent_hex_data
            print(f"Group {group_id}: Found {len(adjacent_hex_list)} adjacent hexes from other groups for cross-group balancing")
    
    # Initialize environment with adjacent hexes support
    env = MultiZoneEnv(
        riders, drivers, 
        max_moves=100,
        adjacent_hexes_data=adjacent_hexes_data,
        current_group_size=len(riders)
    )
    
    # Agent state size includes both current group and adjacent hexes
    agent = DQNAgent(state_size=env.num_zones)
    episodes = 100

    best_agent_reward = -float('inf')
    best_agent_state, best_agent_moves, best_agent_final_drivers, best_agent_final_riders = None, None, None, None

    # Track episode rewards
    episode_rewards = []

    for e in range(episodes):
        state = env.reset()
        done = False
        episode_move_rewards = []

        while not done:
            (f, t, num), idx = agent.act(state)
            if num == 0 or idx is None:
                break
            next_state, reward, done = env.step((f, t, num))
            episode_move_rewards.append(reward)
            agent.remember(state, (f, t, num), idx, reward, next_state, done)
            state = next_state
            agent.replay()

        agent_reward = env.cumulative_reward
        episode_rewards.append(agent_reward)

        if agent_reward > best_agent_reward:
            best_agent_reward = agent_reward
            # Only store state for current group (not adjacent hexes)
            best_agent_state = env.state[:env.current_group_size].copy()
            best_agent_moves = env.dispatch_summary.copy()
            best_agent_final_drivers = env.drivers[:env.current_group_size].copy()
            best_agent_final_riders = env.riders[:env.current_group_size].copy()

        if (e+1) % 50 == 0 or e == 0:
            print(f"Episode {e+1:04d} | Reward={agent_reward:7.2f} | Eps={agent.epsilon:.3f}")

    # Calculate oracle results (only for current group)
    env.reset()
    oracle_state, oracle_final_drivers, oracle_moves = Oracle.final_balance(env)
    # Oracle also only considers current group
    oracle_state = oracle_state[:env.current_group_size] if len(oracle_state) > env.current_group_size else oracle_state
    oracle_final_drivers = oracle_final_drivers[:env.current_group_size] if len(oracle_final_drivers) > env.current_group_size else oracle_final_drivers
    # Filter oracle moves to only include those within current group bounds
    if oracle_moves:
        filtered_oracle_moves = []
        for move in oracle_moves:
            if len(move) >= 3:
                f, t, num = move[0], move[1], move[2]
                # Only include moves that involve current group hexes
                if f < env.current_group_size or t < env.current_group_size:
                    filtered_oracle_moves.append((f, t, num))
        oracle_moves = filtered_oracle_moves
    oracle_score, oracle_perfect, oracle_imbalance = performance_score(oracle_state, env.riders[:env.current_group_size])
    
    # Calculate agent performance score
    agent_score, _, _ = performance_score(best_agent_state, best_agent_final_riders)

    # Filter and map moves to handle cross-group moves properly
    # Create mapping for adjacent hex indices to hex IDs
    adjacent_hex_index_map = {}
    if adjacent_hex_list:
        for idx, hex_id in enumerate(adjacent_hex_list):
            adjacent_hex_index_map[env.current_group_size + idx] = hex_id
    
    # Filter moves to only include those involving current group hexes
    # For cross-group moves, we keep them but need to handle mapping in output
    filtered_moves = []
    for move in best_agent_moves:
        if len(move) == 4:  # (from_z, to_z, num, is_cross_group)
            f, t, num, is_cross_group = move
        else:  # Legacy format
            f, t, num = move
            is_cross_group = (f >= env.current_group_size) or (t >= env.current_group_size)
        
        # Only include moves that involve current group hexes
        if f < env.current_group_size or t < env.current_group_size:
            filtered_moves.append((f, t, num))
    
    # Return final JSON output for this group
    # Pass adjacent hex mapping so output can properly identify cross-group moves
    json_output = generate_json_output(
        best_agent_state, best_agent_final_drivers, best_agent_final_riders, filtered_moves,
        oracle_state=oracle_state, oracle_final_drivers=oracle_final_drivers, 
        oracle_final_riders=env.riders[:env.current_group_size], oracle_moves=oracle_moves,
        agent_score=agent_score, oracle_score=oracle_score,
        riders=riders, drivers=drivers,
        relocation_success_rate=None,
        zone_confidence_scores=None,
        move_confidence_scores=None,
        avg_reward_per_episode=np.mean(episode_rewards),
        episode_cumulative_reward={i: r for i, r in enumerate(episode_rewards)},
        hex_ids=hex_ids,  # Pass hex IDs for mapping (only current group)
        adjacent_hex_index_map=adjacent_hex_index_map  # Map for adjacent hex indices
    )

    return json_output


# from src.synthaticTaxiData.group_hexes_connected import (
#     groups_to_json, groups, RIDER_COUNTS, DRIVER_COUNTS
# )
# group_json = groups_to_json(groups, RIDER_COUNTS, DRIVER_COUNTS)

# # Train for group 2 only
# results_group2 = train_single_group(group_json, 4)
# print(json.dumps(results_group2, indent=3))






# def train():
#     riders = [14, 6, 19, 18, 20,25, 29, 12, 17, 22,16, 19, 21, 18, 24,20, 15, 27, 23, 14,18, 16, 19, 22, 26]
#     drivers = [15, 20, 15, 14, 15,15, 16, 14, 18, 20,17, 18, 19, 16, 22,21, 16, 25, 21, 15,17, 18, 20, 21, 24]

#     env = MultiZoneEnv(riders, drivers, max_moves=100)
#     agent = DQNAgent(state_size=len(riders))
#     episodes = 100

#     best_agent_reward = -float('inf')
#     best_agent_state, best_agent_moves, best_agent_final_drivers, best_agent_final_riders = None, None, None, None
#     scores, perfects, imbalances = [], [], []
    
#     # Track metrics for result calculation
#     episode_rewards = []
#     episode_successful_moves = []
#     episode_total_moves = []

#     for e in range(episodes):
#         state = env.reset()
#         done = False
#         episode_move_rewards = []  # Track rewards for moves in this episode

#         while not done:
#             (f, t, num), idx = agent.act(state)
#             if num == 0 or idx is None:
#                 break
#             next_state, reward, done = env.step((f, t, num))
#             episode_move_rewards.append(reward)
#             agent.remember(state, (f, t, num), idx, reward, next_state, done)
#             state = next_state
#             agent.replay()

#         agent_reward = env.cumulative_reward
#         agent_state = env.state.copy()
#         agent_moves = env.dispatch_summary.copy()
#         agent_final_drivers = env.drivers.copy()
#         agent_final_riders = env.riders.copy()
#         episode_score, perfect_fraction, normalized_imbalance = performance_score(agent_state, agent_final_riders)

#         scores.append(episode_score)
#         perfects.append(perfect_fraction)
#         imbalances.append(normalized_imbalance)
        
#         # Track metrics
#         episode_rewards.append(agent_reward)
#         successful_moves = sum(1 for r in episode_move_rewards if r > 0)
#         episode_successful_moves.append(successful_moves)
#         episode_total_moves.append(len(episode_move_rewards))

#         if agent_reward > best_agent_reward:
#             best_agent_reward = agent_reward
#             best_agent_state = agent_state.copy()
#             best_agent_moves = agent_moves.copy()
#             best_agent_final_drivers = agent_final_drivers.copy()
#             best_agent_final_riders = agent_final_riders.copy()

#         if (e+1) % 50 == 0 or e == 0:
#             print(f"Episode {e+1:04d} | Reward={agent_reward:7.2f} | "
#                   f"Score={episode_score:.3f} | Perfect={perfect_fraction:.3f} | "
#                   f"Normalized Imbalance={normalized_imbalance:.3f} | Eps={agent.epsilon:.3f}")

#     # Oracle
#     env.reset()
#     oracle_state, oracle_final_drivers, oracle_moves = Oracle.final_balance(env)
#     oracle_score, oracle_perfect, oracle_imbalance = performance_score(oracle_state, env.riders)

#     # Final agent score
#     final_agent_score, _, _ = performance_score(best_agent_state, best_agent_final_riders)

#     # Calculate metrics
#     avg_reward_per_episode = np.mean(episode_rewards) if episode_rewards else 0.0
    
#     # Calculate relocation success rate (percentage of moves with positive reward)
#     total_successful_moves = sum(episode_successful_moves)
#     total_moves = sum(episode_total_moves)
#     relocation_success_rate = (total_successful_moves / total_moves * 100.0) if total_moves > 0 else 0.0
    
#     # Calculate confidence scores for initial state (more meaningful than final balanced state)
#     initial_state = np.array(riders) - np.array(drivers)
#     initial_confidence_zone, initial_confidence_actions = agent.get_confidence_scores(initial_state)
    
#     # Calculate confidence scores for each move in best agent's sequence (based on state before each move)
#     move_confidence_scores = []
#     temp_env = MultiZoneEnv(riders, drivers, max_moves=100)
#     temp_state = temp_env.reset()
#     for move in best_agent_moves:
#         f, t, num = move
#         # Get confidence score based on state BEFORE the move
#         zone_conf, action_conf = agent.get_confidence_scores(temp_state)
#         move_key = f"{f}_to_{t}"
#         move_confidence = action_conf.get(move_key, 0.0)
#         move_confidence_scores.append({
#             "from_zone": int(f),
#             "to_zone": int(t),
#             "confidence_score": float(move_confidence)
#         })
#         # Update state for next move (simulate the move)
#         if num > 0 and f != t and temp_env.drivers[f] >= num:
#             temp_env.drivers[f] -= num
#             temp_env.drivers[t] += num
#             temp_state = temp_env.riders - temp_env.drivers

#     # Create episode vs cumulative reward mapping
#     episode_cumulative_reward = {int(i): float(reward) for i, reward in enumerate(episode_rewards)}

#     # Generate JSON output
#     json_output = generate_json_output(
#         best_agent_state, best_agent_final_drivers, best_agent_final_riders, best_agent_moves,
#         oracle_state, oracle_final_drivers, env.riders, oracle_moves,
#         final_agent_score, oracle_score, riders, drivers,
#         relocation_success_rate=relocation_success_rate,
#         zone_confidence_scores=initial_confidence_zone.tolist(),
#         move_confidence_scores=move_confidence_scores,
#         avg_reward_per_episode=avg_reward_per_episode,
#         episode_cumulative_reward=episode_cumulative_reward
#     )

#     return json_output

# # if __name__ == "__main__":
# #     output = train()
# #     import json
# #     print(json.dumps(output, indent=2))