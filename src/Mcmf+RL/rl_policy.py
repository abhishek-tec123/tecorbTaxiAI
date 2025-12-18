# rl_policy.py
import math, random
import numpy as np
from dfinit import MAX_CAP, HIDDEN, LR, hex_ids

n_hex = len(hex_ids)
n_options = MAX_CAP + 1

class Policy:
    def __init__(self, state_dim, hidden=HIDDEN, lr=LR, seed=42):
        random.seed(seed)
        np.random.seed(seed)

        self.w1 = np.random.randn(hidden, state_dim) * 0.01
        self.b1 = np.zeros((hidden, 1))
        self.w2 = np.random.randn(n_hex * n_options, hidden) * 0.01
        self.b2 = np.zeros((n_hex * n_options, 1))
        self.lr = lr

    def forward(self, state):
        x = state.reshape(-1, 1)
        z = np.tanh(self.w1 @ x + self.b1)
        logits = (self.w2 @ z + self.b2).reshape(n_hex, n_options)
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        return probs, z, x

    def sample(self, state, eps=0.0, force_random=False):
        probs, z, x = self.forward(state)
        caps, logp, chosen = [], 0.0, []

        for i in range(n_hex):
            if force_random or random.random() < eps:
                idx = random.randrange(n_options)
            else:
                idx = np.random.choice(n_options, p=probs[i])
            caps.append(idx)
            chosen.append(idx)
            logp += math.log(probs[i][idx] + 1e-12)

        return caps, logp, probs, z, x, chosen

    def update(self, dw1, db1, dw2, db2):
        self.w1 += self.lr * dw1
        self.b1 += self.lr * db1
        self.w2 += self.lr * dw2
        self.b2 += self.lr * db2
