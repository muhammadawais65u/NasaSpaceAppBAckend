from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import AuthUser, get_current_user
from app.database import repository as repo
from app.schemas.mission import (CreateMissionRequest, DecisionRequest, DecisionResponse,
                                 HistoryResponse, MissionList, MissionState)
from app.services import mission_service

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


@router.post("", response_model=MissionState, status_code=201)
def create(body: CreateMissionRequest | None = None,
           user: AuthUser = Depends(get_current_user)):
    return mission_service.create_mission(user, (body or CreateMissionRequest()).mission_type)


@router.get("", response_model=MissionList)
def list_missions(status: Literal["active", "completed", "failed"] | None = None,
                  limit: int = Query(20, ge=1, le=100),
                  user: AuthUser = Depends(get_current_user)):
    items = repo.list_missions(user, status, limit)
    return {"items": items, "count": len(items)}


@router.get("/{mission_id}", response_model=MissionState)
def get_mission(mission_id: UUID, user: AuthUser = Depends(get_current_user)):
    return repo.get_mission(user, str(mission_id))


@router.post("/{mission_id}/decision", response_model=DecisionResponse)
def decide(mission_id: UUID, body: DecisionRequest,
           user: AuthUser = Depends(get_current_user)):
    return mission_service.submit_decision(user, str(mission_id), body)


@router.get("/{mission_id}/history", response_model=HistoryResponse)
def history(mission_id: UUID, user: AuthUser = Depends(get_current_user)):
    return {"mission_id": mission_id, "items": repo.get_history(user, str(mission_id))}
