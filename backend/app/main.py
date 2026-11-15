from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError

from app.core.config import settings
from app.core.errors import ApiError
from app.database import repository as repo
from app.database.clients import service_client
from app.routes import game, missions, nasa
from app.services.resource_service import InvalidDecision

app = FastAPI(title="Junior Astronaut Mission Trainer API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_methods=["*"], allow_headers=["*"])
for r in (missions.router, nasa.router, game.router):
    app.include_router(r)

MESSAGES = {
    "mission_not_found": "Mission not found.",
    "active_mission_exists": "You already have an active mission.",
    "version_conflict": "The mission changed. Reload it and try again.",
    "mission_not_active": "This mission has already ended.",
    "duplicate_request": "This decision was already processed.",
    "unknown_decision_or_option": "That decision or option does not exist.",
}


def error(status, code, message=None, details=None):
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message or MESSAGES.get(code, code),
        "details": details or {}}})


@app.exception_handler(ApiError)
async def _api(_: Request, e: ApiError):
    return error(e.status, e.code, e.message, e.details)


@app.exception_handler(repo.NotFound)
async def _nf(_: Request, e):
    return error(404, "mission_not_found")


@app.exception_handler(repo.Conflict)
async def _cf(_: Request, e: repo.Conflict):
    return error(409, e.code, details=e.extra)


@app.exception_handler(InvalidDecision)
async def _bad(_: Request, e):
    return error(409 if str(e) == "mission_not_active" else 400, str(e))


@app.exception_handler(RequestValidationError)
async def _val(_: Request, e):
    return error(422, "validation_error", "Request is not valid.",
                 {"errors": jsonable_encoder(e.errors())})


@app.exception_handler(APIError)
async def _db(_: Request, e):
    return error(502, "database_error", "Database request failed.")


@app.get("/health", tags=["system"])
def health(deep: bool = False):
    if deep:
        try:
            service_client().table("nasa_events").select("id").limit(1).execute()
        except Exception:
            return error(503, "database_unreachable", "Database unreachable.")
    return {"status": "ok", "version": app.version}
