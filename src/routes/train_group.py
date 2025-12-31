from fastapi import APIRouter, HTTPException
from src.synthaticTaxiData.group_hexes_connected import (
    groups_to_json, groups, RIDER_COUNTS, DRIVER_COUNTS
)
from src.synthaticTaxiData.plot_rider_driver import HEXES
from pydantic import BaseModel

from zoneBalance.train import train_single_group

router = APIRouter()

class TrainGroupRequest(BaseModel):
    group_id: str

@router.post("/group")
def train_group(payload: TrainGroupRequest):
    """
    Train RL model for a single connected hex group.
    Example JSON:
    {
        "group_id": "group_1"
    }
    """

    group_id = payload.group_id

    group_json = groups_to_json(groups, RIDER_COUNTS, DRIVER_COUNTS)

    print(f"Available groups: {list(group_json.keys())}")

    # ✅ Validate format
    if not group_id.startswith("group_"):
        raise HTTPException(
            status_code=400,
            detail="group_id must be in format 'group_X'"
        )

    # ✅ Validate existence
    if group_id not in group_json:
        raise HTTPException(
            status_code=404,
            detail=f"Group '{group_id}' not found. Available groups: {list(group_json.keys())}"
        )

    # ✅ Extract numeric ID for trainer
    numeric_group_id = group_id.replace("group_", "")

    try:
        # Pass cross-group adjacency information for edge hex balancing
        hex_set = set(HEXES)
        results = train_single_group(
            group_json, numeric_group_id,
            all_groups=groups,
            hex_set=hex_set,
            rider_counts=RIDER_COUNTS,
            driver_counts=DRIVER_COUNTS
        )

        return {
            "status": "success",
            "group_id": group_id,
            "internal_group_id": numeric_group_id,
            "total_groups": len(group_json),
            "results": results
        }

    except KeyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training key error: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}"
        )
