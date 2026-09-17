from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_current_user
from ..models import AuditLog, RefreshToken, User, UserRole
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserRead
from ..security import REFRESH_TOKEN_EXPIRE_DAYS, create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, httponly=True, 
                        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", 
                        samesite="strict", path="/api/v1/auth")


def _issue_tokens(db: Session, user: User, response: Response) -> TokenResponse:
    raw = create_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=hash_refresh_token(raw), expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)))
    db.commit()
    _set_refresh_cookie(response, raw)
    return TokenResponse(access_token=create_access_token(user.id, user.email, user.role.value), user=user)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_optional_current_user),
):
    if actor is not None and actor.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only an administrator may create a user with a selected role")
    if actor is None and payload.role != UserRole.viewer:
        raise HTTPException(status_code=403, detail="Public registration may only create a viewer account")
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    role = payload.role if actor is not None else UserRole.viewer
    user = User(email=email, full_name=payload.full_name, role=role, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(AuditLog(actor_id=actor.id if actor else None, action="register", entity_type="user", entity_id=user.id))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    db.add(AuditLog(actor_id=user.id, action="login", entity_type="user", entity_id=user.id, ip_address=request.client.host if request.client else None))
    result = _issue_tokens(db, user, response)
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token is required")
    stored = next((item for item in db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False))).all() if verify_password(raw, item.token_hash)), None)
    now = datetime.now(timezone.utc)
    if not stored or stored.expires_at.replace(tzinfo=timezone.utc) <= now or not stored.user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    stored.revoked = True
    result = _issue_tokens(db, stored.user, response)
    db.add(AuditLog(actor_id=stored.user_id, action="refresh", entity_type="refresh_token", entity_id=stored.id))
    db.commit()
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token is required")
    stored = next((item for item in db.scalars(select(RefreshToken).where(RefreshToken.revoked.is_(False))).all() if verify_password(raw, item.token_hash)), None)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    stored.revoked = True
    db.add(AuditLog(actor_id=stored.user_id, action="logout", entity_type="refresh_token", entity_id=stored.id))
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api/v1/auth")


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
