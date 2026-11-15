"""Every read and write to the database goes through here.
Supabase when it is configured, local SQLite otherwise."""
from app.core.config import settings
from app.core.errors import Conflict, NotFound  # noqa: F401

if settings.use_supabase:
    from app.database import supabase_store as _store
else:
    from app.database import local_store as _store

DatabaseError = _store.DatabaseError

list_missions = _store.list_missions
get_mission = _store.get_mission
get_history = _store.get_history
find_decision = _store.find_decision
create_mission = _store.create_mission
save_decision = _store.save_decision
upsert_events = _store.upsert_events
read_events = _store.read_events
ping = _store.ping
