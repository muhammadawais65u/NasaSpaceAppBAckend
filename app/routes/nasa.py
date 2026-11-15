from fastapi import APIRouter, Depends, Query

from app.core.security import AuthUser, get_current_user
from app.services import nasa_service as nasa
from app.services import osdr_service as osdr

router = APIRouter(prefix="/api/v1/nasa", tags=["nasa"])


@router.get("/space-weather")
def space_weather(days: int = Query(30, ge=1, le=nasa.MAX_WINDOW_DAYS),
                  types: str = "FLR,CME,GST",
                  limit: int = Query(50, ge=1, le=nasa.MAX_EVENTS),
                  user: AuthUser = Depends(get_current_user)):
    wanted = tuple(t for t in types.upper().split(",") if t in nasa.EVENT_TYPES)
    data = nasa.get_space_weather(wanted or nasa.EVENT_TYPES, days)
    data["game_scenario"] = nasa.derive_alert(data["events"])
    data["events"] = data["events"][:limit]
    return data


@router.get("/health-research")
def health_research(term: str = Query("radiation", min_length=2, max_length=60),
                    limit: int = Query(5, ge=1, le=25),
                    user: AuthUser = Depends(get_current_user)):
    return osdr.search_studies(term, limit)
