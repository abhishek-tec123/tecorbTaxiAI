# dfinit.py
import math, random
import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ----------------------------
# Reward weights
# ----------------------------
W_BALANCED = 12.0
W_OVER = -1.0
W_UNDER = -1.0
W_MOVE_COST = -0.2
W_MOVE_BONUS = 0.4

# ----------------------------
# RL / training config
# ----------------------------
MAX_CAP = 10
EPS_START = 1.0
EPS_MIN = 0.2
FORCE_RANDOM_FIRST = 10

EPISODES = 80
STEPS_PER_EP = 8
GAMMA = 0.95
HIDDEN = 64
LR = 1e-2

# ----------------------------
# Sample data
# ----------------------------
data = [
    ("872a100adffffff", 3, 4),
    ("872a100a8ffffff", 4, 2),
    ("872a100aaffffff", 6, 2),
    ("872a1001effffff", 2, 4),
    ("872a1001cffffff", 4, 2),
    ("872a10003ffffff", 0, 2),
    ("872a1001dffffff", 7, 5),
    ("872a10018ffffff", 3, 1),
]

hex_ids = [h for h, _, _ in data]
df_init = pd.DataFrame(data, columns=["HexID", "Riders", "Drivers"])

# ----------------------------
# Synthetic coordinates
# ----------------------------
def hex_to_coord(h):
    s = sum(ord(c) for c in h)
    return (40.7 + ((s % 50) - 25) * 0.001,
            -74.0 + (((s // 50) % 50) - 25) * 0.001)

coords = {h: hex_to_coord(h) for h in hex_ids}

def euclid_dist(a, b):
    (la, lo) = coords[a]
    (lb, lo2) = coords[b]
    return math.hypot(la - lb, lo - lo2) * 111000.0