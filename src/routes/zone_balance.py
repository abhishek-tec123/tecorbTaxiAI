from fastapi import APIRouter
from zoneBalance.train import train

router = APIRouter()

@router.post("/train")
def run_zone_balance_training():
    """
    Run DQN-based zone balance training and return results
    """
    try:
        result = train()
        return result
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
