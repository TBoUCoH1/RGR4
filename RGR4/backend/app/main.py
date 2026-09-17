import os
import logging
import uuid
import json

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine, get_db
from .deps import get_current_user
from .models import Event, Incident, IncidentStatus, User
from .routers import auth, events, incidents, users


def _origins() -> list[str]:
    return [item.strip() for item in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if item.strip()]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "path": getattr(record, "path", None),
            "user_id": getattr(record, "user_id", None),
            "trace_id": getattr(record, "trace_id", None),
            "status_code": getattr(record, "status_code", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[_handler], force=True)
logger = logging.getLogger("incident_portal")
app = FastAPI(
    title="Incident Portal API",
    root_path="/api/v1"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.warning("request validation failed", extra={"path": request.url.path, "trace_id": trace_id, "status_code": 422})
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": jsonable_encoder(exc.errors()), "trace_id": trace_id}})


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.warning("database integrity conflict", extra={"path": request.url.path, "trace_id": trace_id})
    return JSONResponse(status_code=409, content={"error": {"code": "CONFLICT", "message": "The requested operation conflicts with existing data", "details": None, "trace_id": trace_id}})


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.warning("http error response", extra={"path": request.url.path, "trace_id": trace_id, "status_code": exc.status_code})
    code_by_status = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 422: "VALIDATION_ERROR"}
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    content = {"error": {"code": code_by_status.get(exc.status_code, "REQUEST_ERROR"), "message": message, "details": None, "trace_id": trace_id}}
    headers = exc.headers or {}
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.exception("unhandled server error", extra={"path": request.url.path, "trace_id": trace_id})
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": None, "trace_id": trace_id}})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/api/v1/dashboard/stats", tags=["dashboard"])
@app.get("/api/v1/dashboard", tags=["dashboard"])
def dashboard_stats(_: User = Depends(get_current_user), db = Depends(get_db)):
    return {
        "events": db.scalar(select(func.count(Event.id))) or 0,
        "incidents": db.scalar(select(func.count(Incident.id))) or 0,
        "open_incidents": db.scalar(select(func.count(Incident.id)).where(Incident.status.in_((IncidentStatus.open, IncidentStatus.investigating)))) or 0,
        "active_events": db.scalar(select(func.count(Event.id)).where(Event.status == "active")) or 0,
    }


app.include_router(auth.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    try:
        from ..seed import seed_database
    except ImportError:
        from seed import seed_database

    seed_database()
