# dqn.py
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random

class DQNAgent:
    def __init__(self, state_size, lr=1e-3, gamma=0.95,
                 epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.995,
                 memory_size=20000, batch_size=128, target_update_freq=200):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.state_size = state_size
        self.action_size = state_size * state_size
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.memory = deque(maxlen=memory_size)
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.learn_step_counter = 0

        self.model = self.build_model().to(self.device)
        self.target_model = self.build_model().to(self.device)
        self.update_target(hard=True)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        self.loss_fn = nn.MSELoss()

    def build_model(self):
        return nn.Sequential(
            nn.Linear(self.state_size, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, self.action_size)
        )

    # ------------------ Action mapping ------------------
    def ft_to_idx(self, f, t):
        return f * self.state_size + t

    def idx_to_ft(self, idx):
        f = idx // self.state_size
        t = idx % self.state_size
        return int(f), int(t)

    # ------------------ Mask invalid actions ------------------
    def action_mask(self, state):
        mask = np.zeros(self.action_size, dtype=bool)
        surplus = np.where(state < 0)[0]
        deficit = np.where(state > 0)[0]
        for f in surplus:
            for t in deficit:
                if f != t:
                    mask[self.ft_to_idx(f, t)] = True
        return mask

    # ------------------ Choose action ------------------
    def act(self, state):
        state = np.array(state, dtype=np.float32)
        mask = self.action_mask(state)
        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            return (0, 0, 0), None

        if np.random.rand() < self.epsilon:
            idx = int(np.random.choice(valid_indices))
        else:
            self.model.eval()
            with torch.no_grad():
                st = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
                q = self.model(st).cpu().numpy().flatten()
            q[~mask] = -1e9
            idx = int(np.nanargmax(q))

        f, t = self.idx_to_ft(idx)
        num = int(max(1, min(-int(state[f]), int(state[t])))) if state[f] < 0 and state[t] > 0 else 0
        return (int(f), int(t), int(num)), idx

    # ------------------ Memory ------------------
    def remember(self, state, action, action_idx, reward, next_state, done):
        self.memory.append((state.copy(), action, action_idx, reward, next_state.copy(), done))

    def sample_batch(self):
        batch = random.sample(self.memory, self.batch_size)
        states = np.vstack([b[0] for b in batch]).astype(np.float32)
        actions_idx = np.array([b[2] if b[2] is not None else 0 for b in batch], dtype=np.int64)
        rewards = np.array([b[3] for b in batch]).astype(np.float32)
        next_states = np.vstack([b[4] for b in batch]).astype(np.float32)
        dones = np.array([b[5] for b in batch], dtype=np.uint8)
        return states, actions_idx, rewards, next_states, dones

    # ------------------ Replay ------------------
    def replay(self):
        if len(self.memory) < self.batch_size:
            return

        states, actions_idx, rewards, next_states, dones = self.sample_batch()
        states_t = torch.from_numpy(states).to(self.device)
        next_states_t = torch.from_numpy(next_states).to(self.device)
        actions_idx_t = torch.from_numpy(actions_idx).unsqueeze(1).to(self.device)
        rewards_t = torch.from_numpy(rewards).to(self.device)
        dones_t = torch.from_numpy(dones).to(self.device)

        q_values = self.model(states_t)
        current_q = q_values.gather(1, actions_idx_t).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_model(next_states_t)
            B = next_q_values.shape[0]
            mask = torch.zeros_like(next_q_values, dtype=torch.bool, device=self.device)
            N = self.state_size
            for i in range(B):
                ns = next_states[i]
                surplus = np.where(ns < 0)[0]
                deficit = np.where(ns > 0)[0]
                for f in surplus:
                    for t in deficit:
                        if f != t:
                            mask[i, self.ft_to_idx(f, t)] = True
            next_q_values[~mask] = -1e9
            next_max_q, _ = next_q_values.max(dim=1)
            target_q = rewards_t + (1 - dones_t.float()) * (self.gamma * next_max_q)

        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), 5.0)
        self.optimizer.step()

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        self.learn_step_counter += 1
        if self.learn_step_counter % self.target_update_freq == 0:
            self.update_target(hard=True)

    # ------------------ Update target network ------------------
    def update_target(self, hard=False, tau=0.01):
        if hard:
            self.target_model.load_state_dict(self.model.state_dict())
        else:
            for target_param, param in zip(self.target_model.parameters(), self.model.parameters()):
                target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)

    # ------------------ Confidence scores ------------------
    def get_confidence_scores(self, state):
        state = np.array(state, dtype=np.float32)
        mask = self.action_mask(state)
        valid_indices = np.where(mask)[0]

        if len(valid_indices) == 0:
            return np.zeros(self.state_size), {}

        self.model.eval()
        with torch.no_grad():
            st = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
            q = self.model(st).cpu().numpy().flatten()

        q[~mask] = -1e9
        q_valid = q[valid_indices]
        q_exp = np.exp(q_valid - np.max(q_valid))
        q_probs = q_exp / np.sum(q_exp)

        zone_confidence = np.zeros(self.state_size)
        action_confidence = {}
        for i, idx in enumerate(valid_indices):
            f, t = self.idx_to_ft(idx)
            zone_confidence[f] += q_probs[i]
            zone_confidence[t] += q_probs[i]
            action_confidence[f"{f}_to_{t}"] = float(q_probs[i])

        if np.max(zone_confidence) > 0:
            zone_confidence = zone_confidence / np.max(zone_confidence)

        return zone_confidence, action_confidence
