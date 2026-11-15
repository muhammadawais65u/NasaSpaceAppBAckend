from postgrest.exceptions import APIError

from app.database.clients import service_client, user_client


class NotFound(Exception):
    ...


class Conflict(Exception):
    def __init__(self, code: str, **extra):
        super().__init__(code)
        self.code, self.extra = code, extra


# ---- reads: user-scoped, RLS applies ----
def list_missions(token: str, status: str | None, limit: int = 20) -> list[dict]:
    q = user_client(token).table("mission_runs").select("*")
    if status:
        q = q.eq("mission_status", status)
    return q.order("created_at", desc=True).limit(limit).execute().data


def get_mission(token: str, mission_id: str) -> dict:
    res = (user_client(token).table("mission_runs").select("*")
           .eq("id", mission_id).limit(1).execute())
    if not res.data:
        raise NotFound()  # also returned for other players' missions
    return res.data[0]


def get_history(token: str, mission_id: str) -> list[dict]:
    get_mission(token, mission_id)  # 404 if not yours
    return (user_client(token).table("decision_logs").select("*")
            .eq("mission_id", mission_id).order("day").execute().data)


def find_decision(token: str, mission_id: str, request_id: str) -> dict | None:
    res = (user_client(token).table("decision_logs").select("*")
           .eq("mission_id", mission_id).eq("request_id", request_id)
           .limit(1).execute())
    return res.data[0] if res.data else None


# ---- writes: privileged client, ALWAYS scoped by the verified user_id ----
def create_mission(user_id: str, fields: dict) -> dict:
    try:
        res = service_client().table("mission_runs").insert(
            {**fields, "user_id": user_id}).execute()
    except APIError as e:
        if e.code == "23505":  # one active mission per user
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
        if e.code == "23505":  # duplicate request_id or day
            raise Conflict("duplicate_request")
        raise
    return res.data  # the updated mission row
