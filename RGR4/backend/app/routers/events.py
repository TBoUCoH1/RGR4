from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import AuditLog, Event, EventArea, EventStatus, Incident, IncidentStatus, ResponseTeam, ThreatLevel, User, UserRole
from ..schemas import EventAreaCreate, EventAreaRead, EventCreate, EventRead, EventUpdate, IncidentRead, PaginatedEvents, ResponseTeamCreate, ResponseTeamRead

router = APIRouter(prefix="/events", tags=["events"])


def _audit(db: Session, user: User, action: str, event_id: int, request: Request | None = None):
    db.add(AuditLog(actor_id=user.id, action=action, entity_type="event", entity_id=event_id, ip_address=request.client.host if request and request.client else None))


def _get_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("", response_model=PaginatedEvents)
def list_events(
    status_filter: EventStatus | None = Query(default=None, alias="status"),
    threat_level: ThreatLevel | None = None,
    event_date: date | None = Query(default=None, alias="date"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(Event)
    count_query = select(func.count(Event.id))
    filters = []
    if status_filter:
        filters.append(Event.status == status_filter)
    if threat_level:
        filters.append(Event.threat_level == threat_level)
    if event_date:
        start = datetime.combine(event_date, time.min).replace(tzinfo=timezone.utc)
        end = datetime.combine(event_date, time.max).replace(tzinfo=timezone.utc)
        filters.extend((Event.start_dt <= end, Event.end_dt >= start))
    query = query.where(*filters).order_by(Event.start_dt.desc()).offset(skip).limit(limit)
    return {"items": db.scalars(query).all(), "total": db.scalar(count_query.where(*filters)) or 0, "skip": skip, "limit": limit}


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.coordinator))):
    if payload.start_dt.tzinfo is None or payload.end_dt.tzinfo is None:
        raise HTTPException(status_code=422, detail="start_dt and end_dt must include a timezone")
    event = Event(**payload.model_dump(), created_by=user.id)
    db.add(event)
    db.flush()
    _audit(db, user, "create", event.id, request)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_event(db, event_id)


def _can_manage(event: Event, user: User) -> bool:
    return user.role == UserRole.admin or (user.role == UserRole.coordinator and event.created_by == user.id)


@router.put("/{event_id}", response_model=EventRead)
def update_event(event_id: int, payload: EventCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.coordinator))):
    event = _get_event(db, event_id)
    if not _can_manage(event, user):
        raise HTTPException(status_code=403, detail="Only the event owner or an admin may edit this event")
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    _audit(db, user, "update", event.id, request)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=EventRead)
def patch_event(event_id: int, payload: EventUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.coordinator))):
    event = _get_event(db, event_id)
    if not _can_manage(event, user):
        raise HTTPException(status_code=403, detail="Only the event owner or an admin may edit this event")
    updates = payload.model_dump(exclude_unset=True)
    start = updates.get("start_dt", event.start_dt)
    end = updates.get("end_dt", event.end_dt)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_dt must be after start_dt")
    for key, value in updates.items():
        setattr(event, key, value)
    _audit(db, user, "update", event.id, request)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", response_model=EventRead)
def cancel_event(event_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin))):
    event = _get_event(db, event_id)
    event.status = EventStatus.cancelled
    _audit(db, user, "cancel", event.id, request)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/incidents", response_model=list[IncidentRead])
def event_incidents(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_event(db, event_id)
    return db.scalars(select(Incident).options(selectinload(Incident.updates)).where(Incident.event_id == event_id).order_by(Incident.occurred_at.desc())).all()


@router.get("/{event_id}/stats")
def event_stats(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_event(db, event_id)
    incidents = db.scalar(select(func.count(Incident.id)).where(Incident.event_id == event_id)) or 0
    open_incidents = db.scalar(select(func.count(Incident.id)).where(Incident.event_id == event_id, Incident.status.in_((IncidentStatus.open, IncidentStatus.investigating)))) or 0
    return {"event_id": event_id, "incident_count": incidents, "open_incident_count": open_incidents}


@router.get("/{event_id}/areas", response_model=list[EventAreaRead])
def list_areas(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_event(db, event_id)
    return db.scalars(select(EventArea).where(EventArea.event_id == event_id).order_by(EventArea.name)).all()


@router.post("/{event_id}/areas", response_model=EventAreaRead, status_code=201)
def create_area(event_id: int, payload: EventAreaCreate, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.coordinator))):
    event = _get_event(db, event_id)
    if not _can_manage(event, user):
        raise HTTPException(status_code=403, detail="Only the event owner or an admin may manage areas")
    area = EventArea(event_id=event_id, **payload.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.get("/{event_id}/teams", response_model=list[ResponseTeamRead])
def list_teams(event_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_event(db, event_id)
    return db.scalars(select(ResponseTeam).where(ResponseTeam.event_id == event_id).order_by(ResponseTeam.name)).all()


@router.post("/{event_id}/teams", response_model=ResponseTeamRead, status_code=201)
def create_team(event_id: int, payload: ResponseTeamCreate, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.coordinator))):
    event = _get_event(db, event_id)
    if not _can_manage(event, user):
        raise HTTPException(status_code=403, detail="Only the event owner or an admin may manage teams")
    team = ResponseTeam(event_id=event_id, **payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
