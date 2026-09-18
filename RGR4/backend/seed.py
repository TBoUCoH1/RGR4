from datetime import datetime, timedelta, timezone

from sqlalchemy import select

try:
    from .app.database import Base, SessionLocal, engine
    from .app.models import Event, EventArea, EventStatus, Incident, IncidentSeverity, IncidentStatus, ResponseTeam, ThreatLevel, User, UserRole
    from .app.security import hash_password
except ImportError:
    from app.database import Base, SessionLocal, engine
    from app.models import Event, EventArea, EventStatus, Incident, IncidentSeverity, IncidentStatus, ResponseTeam, ThreatLevel, User, UserRole
    from app.security import hash_password


def seed_database() -> None:
    """Create a usable administrator once, without overwriting application data."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return
        demo_users = [
            ("admin@example.com", "Администратор портала", UserRole.admin),
            ("coordinator@example.com", "Анна Кузнецова", UserRole.coordinator),
            ("officer@example.com", "Илья Соколов", UserRole.security_officer),
            ("analyst@example.com", "Мария Орлова", UserRole.analyst),
            ("viewer@example.com", "Дмитрий Волков", UserRole.viewer),
        ]
        users = [User(email=email, full_name=name, role=role, password_hash=hash_password("Admin1234!")) for email, name, role in demo_users]
        db.add_all(users)
        db.flush()
        admin, coordinator, officer, analyst, viewer = users

        now = datetime.now(timezone.utc)
        events = [
            Event(title="Городской форум безопасности", description="Массовое деловое мероприятие с усиленным пропускным режимом.", location="Центральный выставочный комплекс", start_dt=now - timedelta(hours=1), end_dt=now + timedelta(hours=5), status=EventStatus.active, threat_level=ThreatLevel.high, max_capacity=2500, created_by=coordinator.id),
            Event(title="Открытый концерт на набережной", description="Летняя концертная программа и зоны свободного доступа.", location="Северная набережная", start_dt=now + timedelta(days=2), end_dt=now + timedelta(days=2, hours=6), status=EventStatus.planned, threat_level=ThreatLevel.medium, max_capacity=8000, created_by=coordinator.id),
            Event(title="Тренировка оперативного штаба", description="Завершённое учение по координации реагирования.", location="Учебный центр МЧС", start_dt=now - timedelta(days=4), end_dt=now - timedelta(days=4, hours=-3), status=EventStatus.completed, threat_level=ThreatLevel.low, max_capacity=120, created_by=admin.id),
        ]
        db.add_all(events)
        db.flush()
        db.add_all([
            EventArea(event_id=events[0].id, name="Главный вход", description="Основной поток посетителей", latitude=55.7512, longitude=37.6176, radius_meters=80),
            EventArea(event_id=events[0].id, name="Служебная зона", description="Доступ только для персонала", latitude=55.7541, longitude=37.6202, radius_meters=45),
            ResponseTeam(event_id=events[0].id, name="Группа быстрого реагирования", description="Первичная оценка и локализация угроз", lead_user_id=officer.id, contact="+7 (495) 555-01-20"),
        ])
        incidents = [
            Incident(event_id=events[0].id, reported_by=officer.id, title="Скопление у северного входа", description="Плотный поток посетителей у рамок контроля. Направлена дополнительная группа.", severity=IncidentSeverity.moderate, status=IncidentStatus.investigating, latitude=55.7512, longitude=37.6176, occurred_at=now - timedelta(minutes=38)),
            Incident(event_id=events[0].id, reported_by=officer.id, title="Оставленный предмет", description="Обнаружена бесхозная сумка в зоне ожидания. Периметр ограничен.", severity=IncidentSeverity.serious, status=IncidentStatus.open, latitude=55.7541, longitude=37.6202, occurred_at=now - timedelta(minutes=12)),
            Incident(event_id=events[1].id, reported_by=admin.id, title="Повреждение ограждения", description="Зафиксировано повреждение временного ограждения на восточном секторе площадки.", severity=IncidentSeverity.minor, status=IncidentStatus.resolved, latitude=55.7608, longitude=37.6114, occurred_at=now - timedelta(days=1)),
        ]
        db.add_all(incidents)
        db.commit()


if __name__ == "__main__":
    seed_database()
    print("Database seeded. Login: admin@example.com / Admin1234!")
