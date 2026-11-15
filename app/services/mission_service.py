from app.core import game_config as G
from app.core.config import settings
from app.core.security import AuthUser
from app.database import repository as repo
from app.services import nasa_service as nasa
from app.services.resource_service import State, apply_decision

STATE_FIELDS = ("oxygen_level", "power_level", "water_level", "food_level",
                "radiation_protection_level",
                "score", "current_day", "total_days", "mission_status", "alert_level")


def create_mission(user: AuthUser, mission_type: str = "lunar_outpost") -> dict:
    active = repo.list_missions(user, "active", 1)
    if active:
        raise repo.Conflict("active_mission_exists", mission_id=active[0]["id"])
    weather = nasa.get_space_weather(days=nasa.SCENARIO_LOOKBACK_DAYS)
    scenario = nasa.derive_alert(weather["events"])
    if settings.demo_force_alert:
        scenario = {"alert_level": settings.demo_force_alert, "basis_event_id": None}
    return repo.create_mission(user.id, {
        "mission_type": mission_type, **G.START, "score": 0,
        "total_days": G.TOTAL_DAYS, "alert_level": scenario["alert_level"],
        "scenario_event_id": scenario["basis_event_id"]})


def submit_decision(user: AuthUser, mission_id: str, body) -> dict:
    done = repo.find_decision(user, mission_id, str(body.request_id))
    if done:
        return {"mission": done["state_after"], "outcome": outcome_from_log(done),
                "replayed": True}
    row = repo.get_mission(user, mission_id)
    if body.expected_version not in (None, row["version"]):
        raise repo.Conflict("version_conflict")
    old = State(**{k: row[k] for k in STATE_FIELDS})
    new, outcome = apply_decision(old, body.decision_type, body.selected_option)
    log = {
        "request_id": str(body.request_id), "day": outcome["day_played"],
        "decision_type": body.decision_type, "selected_option": body.selected_option,
        "resource_changes": {k: outcome[k] for k in
                             ("resource_changes", "decision_effects", "daily_drain", "balance_bonus")},
        "score_change": outcome["score_change"], "feedback": outcome["feedback"],
        "nasa_event_id": row.get("scenario_event_id")}
    saved = repo.save_decision(user.id, mission_id, row["version"],
                               {k: getattr(new, k) for k in STATE_FIELDS}, log)
    return {"mission": saved, "outcome": outcome, "replayed": False}


def outcome_from_log(r: dict) -> dict:
    status = r["state_after"]["mission_status"]
    return {**r["resource_changes"], "score_change": r["score_change"], "day_played": r["day"],
            "result": None if status == "active" else status,
            "feedback": r["feedback"]}
