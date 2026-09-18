from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import AuditLog, RefreshToken, User, UserRole
from ..schemas import PaginatedUsers, UserCreate, UserRead, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=PaginatedUsers)
def list_users(role: UserRole | None = None, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.admin))):
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    query = query.offset(skip).limit(limit)
    filters = [User.role == role] if role else []
    return {"items": db.scalars(query).all(), "total": db.scalar(select(func.count(User.id)).where(*filters)) or 0, "skip": skip, "limit": limit}


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(email=email, full_name=payload.full_name, role=payload.role, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    db.add(AuditLog(actor_id=admin.id, action="create", entity_type="user", entity_id=user.id, ip_address=request.client.host if request.client else None))
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.admin))):
    return _user(db, user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    user = _user(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = str(updates["email"]).lower()
        existing = db.scalar(select(User).where(User.email == updates["email"], User.id != user_id))
        if existing:
            raise HTTPException(status_code=409, detail="Email is already registered")
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
        db.query(RefreshToken).filter_by(user_id=user_id, revoked=False).update({"revoked": True})
    for key, value in updates.items():
        setattr(user, key, value)
    db.add(AuditLog(actor_id=admin.id, action="update", entity_type="user", entity_id=user.id, ip_address=request.client.host if request.client else None))
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    user = _user(db, user_id)
    user.is_active = not user.is_active
    db.add(AuditLog(actor_id=admin.id, action="activate" if user.is_active else "deactivate", entity_type="user", entity_id=user.id, ip_address=request.client.host if request.client else None))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    user = _user(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.add(AuditLog(actor_id=admin.id, action="delete", entity_type="user", entity_id=user.id, ip_address=request.client.host if request.client else None))
    db.delete(user)
    db.commit()
