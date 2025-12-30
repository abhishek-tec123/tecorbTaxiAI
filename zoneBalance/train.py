# train.py
import numpy as np
from zoneBalance.dqn import DQNAgent
from zoneBalance.oracle import Oracle
from zoneBalance.helpers import performance_score, generate_json_output

class MultiZoneEnv:
    def __init__(self, riders, drivers, max_moves=50):
        self.riders = np.array(riders, dtype=int)
        self.initial_drivers = np.array(drivers, dtype=int)
        self.max_moves = max_moves
        self.num_zones = len(riders)
        self.reset()

    def reset(self):
        self.drivers = self.initial_drivers.copy()
        self.state = self.riders - self.drivers
        self.moves_done = 0
        self.cumulative_reward = 0.0
        self.prev_imbalance = np.sum(np.abs(self.state))
        self.prev_perfect = np.sum(self.state == 0)
        self.dispatch_summary = []
        return self.state.copy()

    def step(self, action):
        from_z, to_z, num_drivers = action
        num_drivers = min(int(num_drivers), int(self.drivers[from_z]))
        if num_drivers > 0 and from_z != to_z:
            self.drivers[from_z] -= num_drivers
            self.drivers[to_z] += num_drivers
            self.moves_done += 1
            self.dispatch_summary.append((from_z, to_z, int(num_drivers)))
        self.state = self.riders - self.drivers
        reward = self.calculate_reward()
        self.cumulative_reward += reward
        done = self.moves_done >= self.max_moves
        return self.state.copy(), reward, done

    def calculate_reward(self):
        current_imbalance = np.sum(np.abs(self.state))
        current_perfect = np.sum(self.state == 0)
        reward = (self.prev_imbalance - current_imbalance) * 3.0
        reward += 5.0 * (current_perfect - self.prev_perfect)
        self.prev_imbalance = current_imbalance
        self.prev_perfect = current_perfect
        return float(reward)

def train():
    riders = [14, 6, 19, 18, 20,25, 29, 12, 17, 22,16, 19, 21, 18, 24,20, 15, 27, 23, 14,18, 16, 19, 22, 26]
    drivers = [15, 20, 15, 14, 15,15, 16, 14, 18, 20,17, 18, 19, 16, 22,21, 16, 25, 21, 15,17, 18, 20, 21, 24]

    env = MultiZoneEnv(riders, drivers, max_moves=100)
    agent = DQNAgent(state_size=len(riders))
    episodes = 100

    best_agent_reward = -float('inf')
    best_agent_state, best_agent_moves, best_agent_final_drivers, best_agent_final_riders = None, None, None, None
    scores, perfects, imbalances = [], [], []
    
    # Track metrics for result calculation
    episode_rewards = []
    episode_successful_moves = []
    episode_total_moves = []

    for e in range(episodes):
        state = env.reset()
        done = False
        episode_move_rewards = []  # Track rewards for moves in this episode

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
        agent_state = env.state.copy()
        agent_moves = env.dispatch_summary.copy()
        agent_final_drivers = env.drivers.copy()
        agent_final_riders = env.riders.copy()
        episode_score, perfect_fraction, normalized_imbalance = performance_score(agent_state, agent_final_riders)

        scores.append(episode_score)
        perfects.append(perfect_fraction)
        imbalances.append(normalized_imbalance)
        
        # Track metrics
        episode_rewards.append(agent_reward)
        successful_moves = sum(1 for r in episode_move_rewards if r > 0)
        episode_successful_moves.append(successful_moves)
        episode_total_moves.append(len(episode_move_rewards))

        if agent_reward > best_agent_reward:
            best_agent_reward = agent_reward
            best_agent_state = agent_state.copy()
            best_agent_moves = agent_moves.copy()
            best_agent_final_drivers = agent_final_drivers.copy()
            best_agent_final_riders = agent_final_riders.copy()

        if (e+1) % 50 == 0 or e == 0:
            print(f"Episode {e+1:04d} | Reward={agent_reward:7.2f} | "
                  f"Score={episode_score:.3f} | Perfect={perfect_fraction:.3f} | "
                  f"Normalized Imbalance={normalized_imbalance:.3f} | Eps={agent.epsilon:.3f}")

    # Oracle
    env.reset()
    oracle_state, oracle_final_drivers, oracle_moves = Oracle.final_balance(env)
    oracle_score, oracle_perfect, oracle_imbalance = performance_score(oracle_state, env.riders)

    # Final agent score
    final_agent_score, _, _ = performance_score(best_agent_state, best_agent_final_riders)

    # Calculate metrics
    avg_reward_per_episode = np.mean(episode_rewards) if episode_rewards else 0.0
    
    # Calculate relocation success rate (percentage of moves with positive reward)
    total_successful_moves = sum(episode_successful_moves)
    total_moves = sum(episode_total_moves)
    relocation_success_rate = (total_successful_moves / total_moves * 100.0) if total_moves > 0 else 0.0
    
    # Calculate confidence scores for initial state (more meaningful than final balanced state)
    initial_state = np.array(riders) - np.array(drivers)
    initial_confidence_zone, initial_confidence_actions = agent.get_confidence_scores(initial_state)
    
    # Calculate confidence scores for each move in best agent's sequence (based on state before each move)
    move_confidence_scores = []
    temp_env = MultiZoneEnv(riders, drivers, max_moves=100)
    temp_state = temp_env.reset()
    for move in best_agent_moves:
        f, t, num = move
        # Get confidence score based on state BEFORE the move
        zone_conf, action_conf = agent.get_confidence_scores(temp_state)
        move_key = f"{f}_to_{t}"
        move_confidence = action_conf.get(move_key, 0.0)
        move_confidence_scores.append({
            "from_zone": int(f),
            "to_zone": int(t),
            "confidence_score": float(move_confidence)
        })
        # Update state for next move (simulate the move)
        if num > 0 and f != t and temp_env.drivers[f] >= num:
            temp_env.drivers[f] -= num
            temp_env.drivers[t] += num
            temp_state = temp_env.riders - temp_env.drivers

    # Create episode vs cumulative reward mapping
    episode_cumulative_reward = {int(i): float(reward) for i, reward in enumerate(episode_rewards)}

    # Generate JSON output
    json_output = generate_json_output(
        best_agent_state, best_agent_final_drivers, best_agent_final_riders, best_agent_moves,
        oracle_state, oracle_final_drivers, env.riders, oracle_moves,
        final_agent_score, oracle_score, riders, drivers,
        relocation_success_rate=relocation_success_rate,
        zone_confidence_scores=initial_confidence_zone.tolist(),
        move_confidence_scores=move_confidence_scores,
        avg_reward_per_episode=avg_reward_per_episode,
        episode_cumulative_reward=episode_cumulative_reward
    )

    return json_output

if __name__ == "__main__":
    output = train()
    import json
    print(json.dumps(output, indent=2))
