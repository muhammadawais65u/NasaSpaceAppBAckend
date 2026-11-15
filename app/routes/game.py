from fastapi import APIRouter

from app.core import game_config as G

router = APIRouter(prefix="/api/v1/game", tags=["game"])


@router.get("/config")
def game_config():
    return {"resource_range": [G.RESOURCE_MIN, G.RESOURCE_MAX],
            "total_days": G.TOTAL_DAYS, "start": G.START,
            "daily_drain": G.DAILY_DRAIN,
            "alert_radiation_multiplier": G.ALERT_RADIATION_MULTIPLIER,
            "is_game_design": True,
            "missions": [{"day": i, **m} for i, m in enumerate(G.MISSIONS, 1)],
            "decisions": G.DECISIONS}
