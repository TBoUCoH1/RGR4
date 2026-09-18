from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuditLog, User, UserRole
from app.schemas import AuditLogPagination, AuditLogRead

router = APIRouter(prefix="/audit-log", tags=["audit"])

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для доступа к журналу аудита"
        )
    return current_user

@router.get("", response_model=AuditLogPagination)
def get_audit_logs(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * limit
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    items = []
    for log in logs:
        item = AuditLogRead.model_validate(log)
        item.actor_username = log.actor.username if log.actor else "Система / Аноним"
        items.append(item)

    return {"items": items, "total": total, "page": page, "limit": limit}