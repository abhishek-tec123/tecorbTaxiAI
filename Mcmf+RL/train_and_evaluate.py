# train_and_evaluate.py
import math, random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from dfinit import *
from mcmf import solve_min_cost_driver_relocation
from rl_policy import Policy

# ----------------------------
# Forecaster
# ----------------------------
class Forecaster:
    def __init__(self, alpha=0.4):
        self.alpha = alpha
        self.level = {h: None for h in hex_ids}

    def update(self, h, obs):
        if self.level[h] is None:
            self.level[h] = float(obs)
        else:
            self.level[h] = self.alpha * obs + (1 - self.alpha) * self.level[h]

    def forecast(self, h):
        return self.level[h] if self.level[h] is not None else 0.0


# ----------------------------
# Environment
# ----------------------------
class HexEnv:
    def __init__(self, df, forecaster, seed=0):
        self.base_df = df.copy()
        self.df = df.copy()
        self.forecaster = forecaster
        random.seed(seed)
        np.random.seed(seed)

        for _, r in self.df.iterrows():
            self.forecaster.update(r.HexID, r.Riders)

    def reset(self):
        self.df = self.base_df.copy()
        return self.state_vector()

    def state_vector(self):
        vec = []
        for _, r in self.df.iterrows():
            f = self.forecaster.forecast(r.HexID)
            vec.extend([
                r.Riders / 10.0,
                r.Drivers / 10.0,
                (r.Drivers - r.Riders) / 10.0,
                f / 10.0
            ])
        return np.array(vec, dtype=np.float32)

    def step(self, moves):
        for s, d, m in moves:
            avail = int(self.df.loc[self.df.HexID == s, "Drivers"].iloc[0])
            m = min(avail, m)
            self.df.loc[self.df.HexID == s, "Drivers"] -= m
            self.df.loc[self.df.HexID == d, "Drivers"] += m

        self.df["Drivers"] = self.df["Drivers"].clip(lower=0)

        # ✅ FIXED riders reset (matches original code)
        static = self.base_df.set_index("HexID")["Riders"]
        self.df["Riders"] = self.df["HexID"].map(static)

        balanced = oversupply = undersupply = 0
        for _, r in self.df.iterrows():
            if r.Drivers == r.Riders:
                balanced += 1
            elif r.Drivers > r.Riders:
                oversupply += r.Drivers - r.Riders
            else:
                undersupply += r.Riders - r.Drivers

        reward = (
            W_BALANCED * balanced +
            W_OVER * oversupply +
            W_UNDER * undersupply
        )

        return self.state_vector(), reward, {
            "balanced": balanced,
            "oversupply_amt": oversupply,
            "undersupply_amt": undersupply
        }



# ----------------------------
# Training (PRINTS IDENTICAL)
# ----------------------------
def train(env, policy):
    logs = []

    for ep in range(EPISODES):
        state = env.reset()
        eps = max(EPS_MIN, EPS_START * (1 - ep / EPISODES))
        force_random = ep < FORCE_RANDOM_FIRST
        total_reward = 0.0
        episode = []

        for _ in range(STEPS_PER_EP):
            caps, logp, probs, z, x, chosen = policy.sample(
                state, eps=eps, force_random=force_random
            )

            per_hex_caps = {hex_ids[i]: caps[i] for i in range(len(hex_ids))}
            moves = solve_min_cost_driver_relocation(env.df, per_hex_caps)

            move_cost = sum(
                m * (euclid_dist(s, d) / 1000.0) for s, d, m in moves
            )
            total_moved = sum(m for _, _, m in moves)

            state, base_reward, info = env.step(moves)

            reward = (
                base_reward +
                W_MOVE_COST * (-move_cost) +
                W_MOVE_BONUS * total_moved
            )

            episode.append((state, probs, z, x, caps, reward))
            total_reward += reward

        logs.append(total_reward)

        if (ep + 1) % 10 == 0 or ep == 0:
            avg10 = np.mean(logs[-10:]) if len(logs) >= 10 else logs[-1]
            print(
                f"Ep {ep+1}/{EPISODES} "
                f"total_reward={total_reward:.2f} "
                f"avg_last10={avg10:.2f} "
                f"eps={eps:.3f} "
                f"force_rand={force_random}"
            )

    return logs


# ----------------------------
# Evaluation (PRINTS IDENTICAL)
# ----------------------------
def evaluate(env, policy):
    state = env.reset()
    rows = []

    for t in range(12):
        caps, _, _, _, _, _ = policy.sample(state, eps=0.0)
        per_hex_caps = {hex_ids[i]: caps[i] for i in range(len(hex_ids))}
        moves = solve_min_cost_driver_relocation(env.df, per_hex_caps)

        move_cost = sum(
            m * (euclid_dist(s, d) / 1000.0) for s, d, m in moves
        )
        total_moved = sum(m for _, _, m in moves)

        state, base_reward, info = env.step(moves)

        reward = (
            base_reward +
            W_MOVE_COST * (-move_cost) +
            W_MOVE_BONUS * total_moved
        )

        if moves:
            for s, d, m in moves:
                rows.append({
                    "t": t,
                    "driver_src": s,
                    "driver_dst": d,
                    "drivers_moved": m,
                    **info,
                    "move_cost_km": round(move_cost, 3),
                    "total_moved": total_moved,
                    "reward": round(reward, 2)
                })
        else:
            rows.append({
                "t": t,
                "driver_src": "",
                "driver_dst": "",
                "drivers_moved": 0,
                **info,
                "move_cost_km": round(move_cost, 3),
                "total_moved": total_moved,
                "reward": round(reward, 2)
            })

    return pd.DataFrame(rows)
