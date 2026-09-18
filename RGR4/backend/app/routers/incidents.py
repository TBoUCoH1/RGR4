from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import AuditLog, Event, Incident, IncidentSeverity, IncidentStatus, IncidentUpdate, User, UserRole
from ..schemas import IncidentCreate, IncidentRead, IncidentStatusUpdate, IncidentUpdateRequest, PaginatedIncidents

router = APIRouter(prefix="/incidents", tags=["incidents"])
READ_ROLES = (UserRole.admin, UserRole.coordinator, UserRole.security_officer, UserRole.analyst, UserRole.viewer)


def _get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.scalar(select(Incident).options(selectinload(Incident.updates)).where(Incident.id == incident_id))
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.security_officer))):
    if not db.get(Event, payload.event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    values = payload.model_dump()
    values["occurred_at"] = values["occurred_at"] or datetime.now(timezone.utc)
    incident = Incident(**values, reported_by=user.id)
    db.add(incident)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="create", entity_type="incident", entity_id=incident.id, ip_address=request.client.host if request.client else None))
    db.commit()
    return _get_incident(db, incident.id)


@router.get("/map", response_model=list[IncidentRead])
def incident_map(db: Session = Depends(get_db), _: User = Depends(require_role(*READ_ROLES))):
    return db.scalars(select(Incident).options(selectinload(Incident.updates)).where(Incident.latitude.is_not(None), Incident.longitude.is_not(None)).order_by(Incident.occurred_at.desc())).all()


@router.get("", response_model=PaginatedIncidents)
def list_incidents(
    event_id: int | None = None,
    severity: IncidentSeverity | None = None,
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*READ_ROLES)),
):
    filters = []
    if event_id is not None:
        filters.append(Incident.event_id == event_id)
    if severity:
        filters.append(Incident.severity == severity)
    if status_filter:
        filters.append(Incident.status == status_filter)
    query = select(Incident).options(selectinload(Incident.updates)).where(*filters).order_by(Incident.occurred_at.desc()).offset(skip).limit(limit)
    total = db.scalar(select(func.count(Incident.id)).where(*filters)) or 0
    return {"items": db.scalars(query).all(), "total": total, "skip": skip, "limit": limit}


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(*READ_ROLES))):
    return _get_incident(db, incident_id)


@router.put("/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdateRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.security_officer, UserRole.coordinator))):
    incident = _get_incident(db, incident_id)
    if user.role != UserRole.admin and incident.reported_by != user.id:
        raise HTTPException(status_code=403, detail="Only the reporter or an admin may edit this incident")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, key, value)
    db.add(AuditLog(actor_id=user.id, action="update", entity_type="incident", entity_id=incident.id, ip_address=request.client.host if request.client else None))
    db.commit()
    return _get_incident(db, incident.id)


@router.patch("/{incident_id}/status", response_model=IncidentRead)
def update_status(incident_id: int, payload: IncidentStatusUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin, UserRole.analyst, UserRole.coordinator))):
    incident = _get_incident(db, incident_id)
    order = {IncidentStatus.open: 0, IncidentStatus.investigating: 1, IncidentStatus.resolved: 2, IncidentStatus.closed: 3}
    if order[payload.status] < order[incident.status]:
        raise HTTPException(status_code=422, detail="Incident status cannot move backwards")
    incident.status = payload.status
    incident.resolution = payload.resolution or incident.resolution
    if payload.status in (IncidentStatus.resolved, IncidentStatus.closed) and not incident.resolved_at:
        incident.resolved_at = datetime.now(timezone.utc)
    incident.updates.append(IncidentUpdate(user_id=user.id, status=payload.status, comment=payload.comment))
    db.add(AuditLog(actor_id=user.id, action="status_change", entity_type="incident", entity_id=incident.id, ip_address=request.client.host if request.client else None))
    db.commit()
    return _get_incident(db, incident.id)


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role(UserRole.admin))):
    incident = _get_incident(db, incident_id)
    db.add(AuditLog(actor_id=user.id, action="delete", entity_type="incident", entity_id=incident.id, ip_address=request.client.host if request.client else None))
    db.delete(incident)
    db.commit()
