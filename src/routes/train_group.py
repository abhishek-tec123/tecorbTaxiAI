from fastapi import APIRouter, HTTPException
from src.synthaticTaxiData.group_hexes_connected import (
    groups_to_json, groups, RIDER_COUNTS, DRIVER_COUNTS
)
from zoneBalance.train import train_single_group

router = APIRouter()


@router.post("/group/{group_id}")
def train_group(group_id: str):
    """
    Train RL model for a single connected hex group.
    Example group_id: group_1
    """

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

    # ✅ Extract numeric ID
    numeric_group_id = group_id.replace("group_", "")

    try:
        results = train_single_group(group_json, numeric_group_id)

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
