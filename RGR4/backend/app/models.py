from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    admin = "admin"
    coordinator = "coordinator"
    security_officer = "security_officer"
    analyst = "analyst"
    viewer = "viewer"


class EventStatus(str, Enum):
    planned = "planned"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ThreatLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentSeverity(str, Enum):
    minor = "minor"
    moderate = "moderate"
    serious = "serious"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    closed = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, name="user_role"), default=UserRole.viewer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="creator")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="reporter")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("end_dt > start_dt", name="events_dates_check"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(512))
    start_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[EventStatus] = mapped_column(SqlEnum(EventStatus, name="event_status"), default=EventStatus.planned, index=True)
    threat_level: Mapped[ThreatLevel] = mapped_column(SqlEnum(ThreatLevel, name="threat_level"), default=ThreatLevel.low)
    max_capacity: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(back_populates="events")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    areas: Mapped[list["EventArea"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    response_teams: Mapped[list["ResponseTeam"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[IncidentSeverity] = mapped_column(SqlEnum(IncidentSeverity, name="incident_severity"), default=IncidentSeverity.minor, index=True)
    status: Mapped[IncidentStatus] = mapped_column(SqlEnum(IncidentStatus, name="incident_status"), default=IncidentStatus.open, index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    event: Mapped[Event] = relationship(back_populates="incidents")
    reporter: Mapped[User] = relationship(back_populates="incidents")
    updates: Mapped[list["IncidentUpdate"]] = relationship(back_populates="incident", cascade="all, delete-orphan")


class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[IncidentStatus | None] = mapped_column(SqlEnum(IncidentStatus, name="incident_update_status"))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Incident] = relationship(back_populates="updates")
    user: Mapped[User] = relationship()


class ResponseTeam(Base):
    __tablename__ = "response_teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    lead_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    contact: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(back_populates="response_teams")
    lead_user: Mapped[User | None] = relationship()


class EventArea(Base):
    __tablename__ = "event_areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    radius_meters: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(back_populates="areas")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    actor: Mapped[User | None] = relationship()
