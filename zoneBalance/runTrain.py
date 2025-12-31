import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from src.synthaticTaxiData.group_hexes_connected import (
    groups_to_json, groups, RIDER_COUNTS, DRIVER_COUNTS
)
from src.synthaticTaxiData.plot_rider_driver import HEXES
from train import train_single_group
import json

group_json = groups_to_json(groups, RIDER_COUNTS, DRIVER_COUNTS)

# Train for group 2 only with cross-group adjacency support
hex_set = set(HEXES)
results_group2 = train_single_group(
    group_json, 4,
    all_groups=groups,
    hex_set=hex_set,
    rider_counts=RIDER_COUNTS,
    driver_counts=DRIVER_COUNTS
)
print(json.dumps(results_group2, indent=3))