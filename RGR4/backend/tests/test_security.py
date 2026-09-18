import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import AuditLog, User, UserRole
from app.security import create_access_token, hash_password, verify_password

API_PREFIX = "/api/v1"


def _get_error_msg(response) -> str:
    data = response.json()
    if isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            return str(data["error"].get("message", ""))
        if "detail" in data:
            return str(data["detail"])
    return ""


@pytest.fixture
def client():
    return TestClient(app, root_path="")


@pytest.fixture
def db_session():
    gen = get_db()
    session: Session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.fixture
def admin_user(db_session: Session):
    user = db_session.scalar(select(User).where(User.role == UserRole.admin))
    if not user:
        user = User(
            email="admin_fixture@example.com",
            full_name="Admin Fixture",
            role=UserRole.admin,
            password_hash=hash_password("AdminPass123!"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User):
    return create_access_token(admin_user.id, admin_user.email, admin_user.role.value)


@pytest.fixture
def viewer_user(db_session: Session):
    user = db_session.scalar(select(User).where(User.role == UserRole.viewer))
    if not user:
        user = User(
            email="viewer_fixture@example.com",
            full_name="Viewer Fixture",
            role=UserRole.viewer,
            password_hash=hash_password("ViewerPass123!"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def viewer_token(viewer_user: User):
    return create_access_token(viewer_user.id, viewer_user.email, viewer_user.role.value)


# 1. Доступ к закрытым ресурсам без авторизации (401 / 403)
def test_unauthorized_access_blocked(client: TestClient):
    response = client.get(f"{API_PREFIX}/incidents")
    assert response.status_code in (401, 403)

    response_audit = client.get(f"{API_PREFIX}/audit-log")
    assert response_audit.status_code in (401, 403)


# 2. Неудачный вход с фиксацией инцидента в AuditLog
def test_login_failed_records_to_audit_log(client: TestClient, db_session: Session):
    fake_email = "attacker_audit_test@example.com"
    response = client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": fake_email, "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert _get_error_msg(response) == "Invalid email or password"

    log_entry = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "login_failed")
        .order_by(AuditLog.created_at.desc())
    )
    assert log_entry is not None
    assert log_entry.details.get("attempted_email") == fake_email


# 3. Ролевое разграничение доступа (RBAC / 403 Forbidden)
def test_role_based_access_control(client: TestClient, viewer_token: str):
    headers = {"Authorization": f"Bearer {viewer_token}"}
    payload = {
        "title": "Несанкционированное событие",
        "description": "Попытка создания без прав",
        "start_dt": "2026-10-01T10:00:00Z",
        "end_dt": "2026-10-01T18:00:00Z",
        "threat_level": "low",
        "status": "planned",
    }
    response = client.post(f"{API_PREFIX}/events", json=payload, headers=headers)
    assert response.status_code == 403


# 4. Валидация входных данных и отклонение слабого пароля (422)
def test_input_validation_and_weak_password_rejection(client: TestClient):
    payload = {
        "email": "invalid_pwd_user@example.com",
        "full_name": "Тестовый Пользователь",
        "password": "onlylettersnopassword",  # нет обязательной цифры
    }
    response = client.post(f"{API_PREFIX}/auth/register", json=payload)
    assert response.status_code == 422


# 5. Проверка безопасного хранения паролей в виде bcrypt-хеша
def test_passwords_stored_as_secure_hashes():
    raw_password = "SecretPassword123!"
    hashed = hash_password(raw_password)

    assert raw_password not in hashed
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_password, hashed) is True


# 6. Полный цикл проверки двухфакторной аутентификации (2FA / TOTP)
def test_two_factor_authentication_flow(client: TestClient, db_session: Session):
    secret = pyotp.random_base32()
    user_email = "totp_security_test@example.com"
    pwd = "TotpPassword123!"

    existing = db_session.scalar(select(User).where(User.email == user_email))
    if existing:
        db_session.delete(existing)
        db_session.commit()

    totp_user = User(
        email=user_email,
        full_name="TOTP User",
        password_hash=hash_password(pwd),
        role=UserRole.viewer,
        totp_secret=secret,
        is_totp_enabled=True,
    )
    db_session.add(totp_user)
    db_session.commit()

    # Шаг 1: вход без кода -> 403 totp_required
    res1 = client.post(f"{API_PREFIX}/auth/login", json={"email": user_email, "password": pwd})
    assert res1.status_code == 403
    assert _get_error_msg(res1) == "totp_required"

    # Шаг 2: неверный код -> 401
    res2 = client.post(f"{API_PREFIX}/auth/login", json={"email": user_email, "password": pwd, "code": "000000"})
    assert res2.status_code == 401

    # Шаг 3: валидный TOTP-код -> 200 OK + access_token
    valid_code = pyotp.TOTP(secret).now()
    res3 = client.post(f"{API_PREFIX}/auth/login", json={"email": user_email, "password": pwd, "code": valid_code})
    assert res3.status_code == 200
    assert "access_token" in res3.json()


# 7. Фиксация удаления записи администратором в журнале аудита
def test_deletion_logged_in_audit(client: TestClient, admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {admin_token}"}

    target_email = "delete_target_fixture@example.com"
    existing = db_session.scalar(select(User).where(User.email == target_email))
    if existing:
        db_session.delete(existing)
        db_session.commit()

    target = User(
        email=target_email,
        full_name="Delete Target",
        password_hash=hash_password("Pass12345!"),
        role=UserRole.viewer,
    )
    db_session.add(target)
    db_session.commit()
    target_id = target.id

    del_res = client.delete(f"{API_PREFIX}/users/{target_id}", headers=headers)
    assert del_res.status_code == 204

    audit_entry = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "delete", AuditLog.entity_id == target_id)
    )
    assert audit_entry is not None