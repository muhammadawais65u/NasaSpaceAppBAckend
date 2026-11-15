from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateMissionRequest(BaseModel):
    mission_type: Literal["lunar_outpost"] = "lunar_outpost"


class DecisionRequest(BaseModel):
    decision_type: str = Field(min_length=1, max_length=40)
    selected_option: str = Field(min_length=1, max_length=40)
    request_id: UUID
    expected_version: int | None = Field(default=None, ge=1)


class MissionState(BaseModel):
    id: UUID
    mission_type: str
    mission_status: Literal["active", "completed", "failed"]
    current_day: int
    total_days: int
    oxygen_level: int
    power_level: int
    water_level: int
    food_level: int
    radiation_protection_level: int
    score: int
    alert_level: Literal["calm", "watch", "storm"]
    scenario_event_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime


class MissionList(BaseModel):
    items: list[MissionState]
    count: int


class Outcome(BaseModel):
    decision_effects: dict[str, int]
    daily_drain: dict[str, int]
    resource_changes: dict[str, int]
    balance_bonus: bool
    score_change: int
    day_played: int
    result: Literal["completed", "failed"] | None
    feedback: str


class DecisionResponse(BaseModel):
    mission: MissionState
    outcome: Outcome
    replayed: bool


class HistoryItem(BaseModel):
    day: int
    decision_type: str
    selected_option: str
    score_change: int
    feedback: str | None
    resource_changes: dict
    created_at: datetime


class HistoryResponse(BaseModel):
    mission_id: UUID
    items: list[HistoryItem]
