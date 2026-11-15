from fastapi import APIRouter, Depends, Query

from app.core.security import AuthUser, get_current_user
from app.services import nasa_service as nasa

router = APIRouter(prefix="/api/v1/nasa", tags=["nasa"])


@router.get("/space-weather")
def space_weather(days: int = Query(30, ge=1, le=90),
                  types: str = "FLR,CME,GST",
                  user: AuthUser = Depends(get_current_user)):
    wanted = tuple(t for t in types.upper().split(",") if t in nasa.EVENT_TYPES)
    data = nasa.get_space_weather(wanted or nasa.EVENT_TYPES, days)
    alert = nasa.derive_alert(data["events"])
    alert.pop("basis_event_id")
    data["game_scenario"] = alert
    return data
