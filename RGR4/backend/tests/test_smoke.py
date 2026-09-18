"""Минимальные проверки, не требующие отдельной тестовой БД или httpx."""

import unittest
from datetime import datetime, timedelta, timezone

from app.main import app
from app.models import Base, Incident, User, UserRole
from app.schemas import EventCreate, UserCreate
from app.security import hash_password, verify_password


class ImportAndSchemaSmokeTests(unittest.TestCase):
    def test_fastapi_app_and_expected_routes_are_importable(self):
        self.assertEqual(app.title, "Incident Coordination Portal API")
        routes = {route.path for route in app.routes}
        self.assertIn("/health", routes)
        self.assertIn("/api/v1/auth/login", routes)
        self.assertIn("/api/v1/events", routes)
        self.assertIn("/api/v1/incidents/map", routes)

    def test_domain_tables_are_registered(self):
        self.assertTrue({"users", "events", "incidents", "incident_updates", "event_areas", "response_teams", "refresh_tokens", "audit_logs"}.issubset(Base.metadata.tables))

    def test_password_and_event_date_validation(self):
        with self.assertRaises(ValueError):
            UserCreate(email="person@example.com", full_name="Person", password="password")

        start = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            EventCreate(title="Некорректное событие", start_dt=start, end_dt=start - timedelta(minutes=1))

    def test_password_hashing_backend(self):
        password_hash = hash_password("Admin1234!")
        self.assertTrue(verify_password("Admin1234!", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))

    def test_role_and_model_fields_match_portal_contract(self):
        self.assertEqual({role.value for role in UserRole}, {"admin", "coordinator", "security_officer", "analyst", "viewer"})
        self.assertTrue({"event_id", "reported_by", "severity", "status", "latitude", "longitude"}.issubset(Incident.__table__.columns.keys()))
        self.assertIn("email", User.__table__.columns.keys())


if __name__ == "__main__":
    unittest.main()
