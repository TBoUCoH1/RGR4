from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import EventStatus, IncidentSeverity, IncidentStatus, ThreatLevel, UserRole


Password = Annotated[str, Field(min_length=8, max_length=128)]


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.viewer


class UserCreate(UserBase):
    password: Password

    @model_validator(mode="after")
    def password_has_number(self):
        if not any(char.isdigit() for char in self.password):
            raise ValueError("Password must contain at least one digit")
        return self


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    password: Password | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def password_has_number(self):
        if self.password is not None and not any(char.isdigit() for char in self.password):
            raise ValueError("Password must contain at least one digit")
        return self


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaginatedUsers(BaseModel):
    items: list[UserRead]
    total: int
    skip: int
    limit: int


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=512)
    start_dt: datetime
    end_dt: datetime
    status: EventStatus = EventStatus.planned
    threat_level: ThreatLevel = ThreatLevel.low
    max_capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.end_dt <= self.start_dt:
            raise ValueError("end_dt must be after start_dt")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=512)
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    status: EventStatus | None = None
    threat_level: ThreatLevel | None = None
    max_capacity: int | None = Field(default=None, ge=1)


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedEvents(BaseModel):
    items: list[EventRead]
    total: int
    skip: int
    limit: int


class IncidentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: int
    title: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=1)
    severity: IncidentSeverity = IncidentSeverity.minor
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    occurred_at: datetime | None = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    severity: IncidentSeverity | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class IncidentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: IncidentStatus
    comment: str | None = None
    resolution: str | None = None


class IncidentUpdateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    user_id: int
    status: IncidentStatus | None
    comment: str | None
    created_at: datetime


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reported_by: int
    status: IncidentStatus
    resolved_at: datetime | None
    resolution: str | None
    created_at: datetime
    updated_at: datetime
    updates: list[IncidentUpdateRead] = Field(default_factory=list)


class PaginatedIncidents(BaseModel):
    items: list[IncidentRead]
    total: int
    skip: int
    limit: int


class EventAreaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: float | None = Field(default=None, gt=0)


class EventAreaRead(EventAreaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    created_at: datetime


class ResponseTeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    lead_user_id: int | None = None
    contact: str | None = Field(default=None, max_length=255)


class ResponseTeamRead(ResponseTeamCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    created_at: datetime
