"""Supabase storage. Reads run as the player (RLS); writes use the service role,
always scoped by the verified user id."""
import httpx
from postgrest.exceptions import APIError

from app.core.errors import Conflict, NotFound
from app.core.security import AuthUser
from app.database.clients import service_client, user_client

DatabaseError = (APIError, httpx.HTTPError)

EVENT_COLUMNS = "id,external_event_id,event_type,event_date,summary,data_origin,retrieved_at"


def list_missions(user: AuthUser, status: str | None, limit: int = 20) -> list[dict]:
    q = user_client(user.token).from_("mission_runs").select("*")
    if status:
        q = q.eq("mission_status", status)
    return q.order("created_at", desc=True).limit(limit).execute().data


def get_mission(user: AuthUser, mission_id: str) -> dict:
    res = (user_client(user.token).from_("mission_runs").select("*")
           .eq("id", mission_id).limit(1).execute())
    if not res.data:
        raise NotFound()
    return res.data[0]


def get_history(user: AuthUser, mission_id: str) -> list[dict]:
    get_mission(user, mission_id)
    return (user_client(user.token).from_("decision_logs").select("*")
            .eq("mission_id", mission_id).order("day").execute().data)


def find_decision(user: AuthUser, mission_id: str, request_id: str) -> dict | None:
    res = (user_client(user.token).from_("decision_logs").select("*")
           .eq("mission_id", mission_id).eq("request_id", request_id)
           .limit(1).execute())
    return res.data[0] if res.data else None


def create_mission(user_id: str, fields: dict) -> dict:
    try:
        res = service_client().table("mission_runs").insert(
            {**fields, "user_id": user_id}).execute()
    except APIError as e:
        if e.code == "23505":
            raise Conflict("active_mission_exists")
        raise
    return res.data[0]


def save_decision(user_id: str, mission_id: str, expected_version: int,
                  new_state: dict, log: dict) -> dict:
    try:
        res = service_client().rpc("save_decision", {
            "p_mission_id": mission_id, "p_user_id": user_id,
            "p_expected_version": expected_version,
            "p_new_state": new_state, "p_log": log}).execute()
    except APIError as e:
        if "version_conflict" in (e.message or ""):
            raise Conflict("version_conflict")
        if e.code == "23505":
            raise Conflict("duplicate_request")
        raise
    return res.data[0] if isinstance(res.data, list) else res.data


def upsert_events(rows: list[dict]) -> None:
    service_client().table("nasa_events").upsert(
        rows, on_conflict="source,external_event_id").execute()


def read_events(types, start_iso: str, limit: int) -> list[dict]:
    return (service_client().table("nasa_events").select(EVENT_COLUMNS)
            .in_("event_type", list(types)).gte("event_date", start_iso)
            .order("event_date", desc=True).limit(limit).execute().data)


def ping() -> None:
    service_client().table("nasa_events").select("id").limit(1).execute()
