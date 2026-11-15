"""Local SQLite storage for development without a Supabase project.
Mirrors the tables and guarantees of migrations/*.sql."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from app.core.config import settings
from app.core.errors import Conflict, NotFound
from app.core.security import AuthUser

DatabaseError = (sqlite3.Error,)

SCHEMA = """
create table if not exists nasa_events (
    id text primary key,
    source text not null default 'NASA DONKI',
    external_event_id text not null,
    event_type text not null check (event_type in ('CME','GST','FLR')),
    event_date text not null,
    event_data text not null,
    summary text not null,
    data_origin text not null default 'live_api' check (data_origin in ('live_api','archive')),
    retrieved_at text not null,
    unique (source, external_event_id)
);
create index if not exists nasa_events_type_date_idx on nasa_events (event_type, event_date desc);

create table if not exists mission_runs (
    id text primary key,
    user_id text not null,
    mission_type text not null default 'lunar_outpost'
        check (mission_type in ('lunar_outpost','mars_outpost')),
    mission_status text not null default 'active'
        check (mission_status in ('active','completed','failed')),
    current_day int not null default 1 check (current_day >= 1),
    total_days int not null default 7 check (total_days >= 1),
    oxygen_level int not null check (oxygen_level between 0 and 100),
    power_level int not null check (power_level between 0 and 100),
    water_level int not null check (water_level between 0 and 100),
    food_level int not null check (food_level between 0 and 100),
    radiation_protection_level int not null check (radiation_protection_level between 0 and 100),
    score int not null default 0 check (score >= 0),
    alert_level text not null default 'calm' check (alert_level in ('calm','watch','storm')),
    scenario_event_id text references nasa_events(id) on delete set null,
    version int not null default 1,
    created_at text not null,
    updated_at text not null
);
create index if not exists mission_runs_user_idx on mission_runs (user_id, created_at desc);
create unique index if not exists one_active_mission_per_user
    on mission_runs (user_id) where mission_status = 'active';

create table if not exists decision_logs (
    id text primary key,
    mission_id text not null references mission_runs(id) on delete cascade,
    user_id text not null,
    nasa_event_id text references nasa_events(id) on delete set null,
    request_id text not null,
    day int not null check (day >= 1),
    decision_type text not null,
    selected_option text not null,
    resource_changes text not null,
    score_change int not null,
    feedback text,
    state_after text not null,
    created_at text not null,
    unique (mission_id, request_id),
    unique (mission_id, day)
);
create index if not exists decision_logs_mission_idx on decision_logs (mission_id, day);
"""

MISSION_UPDATE = ("current_day", "mission_status", "oxygen_level", "power_level",
                  "water_level", "food_level",
                  "radiation_protection_level", "score")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db():
    conn = sqlite3.connect(settings.local_db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("pragma foreign_keys = on")
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()


def _log(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["resource_changes"] = json.loads(d["resource_changes"])
    d["state_after"] = json.loads(d["state_after"])
    return d


def list_missions(user: AuthUser, status: str | None, limit: int = 20) -> list[dict]:
    sql, args = "select * from mission_runs where user_id = ?", [user.id]
    if status:
        sql, args = sql + " and mission_status = ?", args + [status]
    with _db() as db:
        return [dict(r) for r in db.execute(
            sql + " order by created_at desc limit ?", args + [limit])]


def get_mission(user: AuthUser, mission_id: str) -> dict:
    with _db() as db:
        row = db.execute("select * from mission_runs where id = ? and user_id = ?",
                         (mission_id, user.id)).fetchone()
    if row is None:
        raise NotFound()
    return dict(row)


def get_history(user: AuthUser, mission_id: str) -> list[dict]:
    get_mission(user, mission_id)
    with _db() as db:
        return [_log(r) for r in db.execute(
            "select * from decision_logs where mission_id = ? and user_id = ? order by day",
            (mission_id, user.id))]


def find_decision(user: AuthUser, mission_id: str, request_id: str) -> dict | None:
    with _db() as db:
        row = db.execute(
            "select * from decision_logs where mission_id = ? and request_id = ? and user_id = ?",
            (mission_id, request_id, user.id)).fetchone()
    return _log(row) if row else None


def create_mission(user_id: str, fields: dict) -> dict:
    now = _now()
    row = {**fields, "id": str(uuid.uuid4()), "user_id": user_id,
           "created_at": now, "updated_at": now}
    cols = ", ".join(row)
    with _db() as db:
        try:
            db.execute(f"insert into mission_runs ({cols}) values ({', '.join('?' * len(row))})",
                       list(row.values()))
        except sqlite3.IntegrityError as e:
            if "user_id" in str(e):
                raise Conflict("active_mission_exists")
            raise
        return dict(db.execute("select * from mission_runs where id = ?", (row["id"],)).fetchone())


def save_decision(user_id: str, mission_id: str, expected_version: int,
                  new_state: dict, log: dict) -> dict:
    """Updates the mission and inserts the log in one transaction."""
    with _db() as db:
        db.execute("begin immediate")
        try:
            cur = db.execute(
                f"update mission_runs set {', '.join(f'{c} = ?' for c in MISSION_UPDATE)}, "
                "version = version + 1, updated_at = ? "
                "where id = ? and user_id = ? and version = ? and mission_status = 'active'",
                [new_state[c] for c in MISSION_UPDATE] + [_now(), mission_id, user_id, expected_version])
            if cur.rowcount == 0:
                raise Conflict("version_conflict")
            saved = dict(db.execute("select * from mission_runs where id = ?", (mission_id,)).fetchone())
            try:
                db.execute(
                    "insert into decision_logs (id, mission_id, user_id, nasa_event_id, request_id, day, "
                    "decision_type, selected_option, resource_changes, score_change, feedback, "
                    "state_after, created_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), mission_id, user_id, log.get("nasa_event_id"),
                     log["request_id"], log["day"], log["decision_type"], log["selected_option"],
                     json.dumps(log["resource_changes"]), log["score_change"], log.get("feedback"),
                     json.dumps(saved), _now()))
            except sqlite3.IntegrityError:
                raise Conflict("duplicate_request")
            db.execute("commit")
        except BaseException:
            db.execute("rollback")
            raise
    return saved


def upsert_events(rows: list[dict]) -> None:
    with _db() as db:
        db.execute("begin")
        db.executemany(
            "insert into nasa_events (id, source, external_event_id, event_type, event_date, "
            "event_data, summary, data_origin, retrieved_at) values (?,?,?,?,?,?,?,?,?) "
            "on conflict (source, external_event_id) do update set event_type = excluded.event_type, "
            "event_date = excluded.event_date, event_data = excluded.event_data, "
            "summary = excluded.summary, data_origin = excluded.data_origin, "
            "retrieved_at = excluded.retrieved_at",
            [(str(uuid.uuid4()), r["source"], r["external_event_id"], r["event_type"],
              r["event_date"], json.dumps(r["event_data"]), json.dumps(r["summary"]),
              r["data_origin"], r["retrieved_at"]) for r in rows])
        db.execute("commit")


def read_events(types, start_iso: str, limit: int) -> list[dict]:
    types = list(types)
    with _db() as db:
        rows = db.execute(
            "select id, external_event_id, event_type, event_date, summary, data_origin, retrieved_at "
            f"from nasa_events where event_type in ({', '.join('?' * len(types))}) "
            "and event_date >= ? order by event_date desc limit ?",
            types + [start_iso, limit]).fetchall()
    return [{**dict(r), "summary": json.loads(r["summary"])} for r in rows]


def ping() -> None:
    with _db() as db:
        db.execute("select id from nasa_events limit 1").fetchone()
