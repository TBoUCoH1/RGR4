"""HTTP-level checks for authentication, authorization, CRUD and error contracts."""

import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.session_factory = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        db = cls.session_factory()
        db.add(User(email="admin@test.example", full_name="Test Admin", role=UserRole.admin, password_hash=hash_password("Admin1234!")))
        db.add(User(email="viewer@test.example", full_name="Test Viewer", role=UserRole.viewer, password_hash=hash_password("Viewer1234")))
        db.commit()
        db.close()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)

    def login(self, email: str, password: str) -> str:
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def create_event(self, token: str, title: str) -> int:
        start = datetime.now(timezone.utc) + timedelta(days=1)
        created = self.client.post("/api/v1/events", headers=self.auth_headers(token), json={"title": title, "start_dt": start.isoformat(), "end_dt": (start + timedelta(hours=2)).isoformat()})
        self.assertEqual(created.status_code, 201, created.text)
        return created.json()["id"]

    def create_user(self, admin_headers: dict, email: str, role: str, password: str = "User1234!"):
        created = self.client.post("/api/v1/users", headers=admin_headers, json={"email": email, "full_name": email, "role": role, "password": password})
        self.assertEqual(created.status_code, 201, created.text)

    def create_incident(self, token: str, event_id: int, **overrides) -> dict:
        payload = {"event_id": event_id, "description": "Test incident", "severity": "moderate"}
        payload.update(overrides)
        created = self.client.post("/api/v1/incidents", headers=self.auth_headers(token), json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        return created.json()

    def test_registration_login_refresh_and_protected_resource(self):
        registered = self.client.post("/api/v1/auth/register", json={"email": "registered-viewer@test.example", "full_name": "Registered Viewer", "password": "Viewer1234"})
        self.assertEqual(registered.status_code, 201, registered.text)
        self.assertEqual(registered.json()["role"], "viewer")
        self.assertNotIn("password", registered.json())

        token = self.login("registered-viewer@test.example", "Viewer1234")
        stats = self.client.get("/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(stats.status_code, 200, stats.text)
        refreshed = self.client.post("/api/v1/auth/refresh")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertNotEqual(refreshed.json()["access_token"], token)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 204)
        self.assertEqual(self.client.post("/api/v1/auth/refresh").status_code, 401)

    def test_public_registration_cannot_assign_privileged_role(self):
        response = self.client.post("/api/v1/auth/register", json={"email": "admin-request@test.example", "full_name": "Untrusted Admin", "role": "admin", "password": "Admin1234!"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_validation_conflict_and_security_headers(self):
        invalid = self.client.post("/api/v1/auth/register", json={"email": "bad-email", "full_name": "", "password": "short"})
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"]["code"], "VALIDATION_ERROR")
        duplicate = self.client.post("/api/v1/auth/register", json={"email": "admin@test.example", "full_name": "Duplicate", "password": "Admin1234!"})
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["error"]["code"], "CONFLICT")
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.headers.get("X-Trace-Id"))

    def test_unauthorized_and_forbidden_are_unified(self):
        unauthorized = self.client.get("/api/v1/dashboard/stats")
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.json()["error"]["code"], "UNAUTHORIZED")

        viewer_token = self.login("viewer@test.example", "Viewer1234")
        forbidden = self.client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "title": "Forbidden event",
                "start_dt": datetime.now(timezone.utc).isoformat(),
                "end_dt": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            },
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["error"]["code"], "FORBIDDEN")

    def test_admin_can_create_update_and_cancel_event(self):
        token = self.login("admin@test.example", "Admin1234!")
        headers = {"Authorization": f"Bearer {token}"}
        start = datetime.now(timezone.utc) + timedelta(days=1)
        created = self.client.post("/api/v1/events", headers=headers, json={"title": "API event", "start_dt": start.isoformat(), "end_dt": (start + timedelta(hours=2)).isoformat()})
        self.assertEqual(created.status_code, 201, created.text)
        event_id = created.json()["id"]
        updated = self.client.patch(f"/api/v1/events/{event_id}", headers=headers, json={"title": "Updated API event"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Updated API event")
        deleted = self.client.delete(f"/api/v1/events/{event_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()["status"], "cancelled")

    def test_admin_user_crud_returns_paginated_collection(self):
        token = self.login("admin@test.example", "Admin1234!")
        headers = {"Authorization": f"Bearer {token}"}
        created = self.client.post("/api/v1/users", headers=headers, json={"email": "crud-user@test.example", "full_name": "CRUD User", "role": "viewer", "password": "Viewer1234"})
        self.assertEqual(created.status_code, 201, created.text)
        user_id = created.json()["id"]
        listed = self.client.get("/api/v1/users?role=viewer&skip=0&limit=10", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertIn("items", listed.json())
        updated = self.client.put(f"/api/v1/users/{user_id}", headers=headers, json={"full_name": "Updated CRUD User"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["full_name"], "Updated CRUD User")
        deleted = self.client.delete(f"/api/v1/users/{user_id}", headers=headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)

    def test_incident_create_list_filter_and_get(self):
        token = self.login("admin@test.example", "Admin1234!")
        headers = self.auth_headers(token)
        event_id = self.create_event(token, "Incident list event")
        incident = self.create_incident(token, event_id, title="Serious incident", severity="serious")
        self.assertEqual(incident["status"], "open")
        self.assertEqual(incident["event_id"], event_id)

        listed = self.client.get(f"/api/v1/incidents?event_id={event_id}&severity=serious&status=open", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        body = listed.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["id"], incident["id"])

        empty = self.client.get(f"/api/v1/incidents?event_id={event_id}&severity=critical", headers=headers)
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json()["total"], 0)

        fetched = self.client.get(f"/api/v1/incidents/{incident['id']}", headers=headers)
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["title"], "Serious incident")

        missing = self.client.get("/api/v1/incidents/999999", headers=headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "NOT_FOUND")

    def test_incident_status_transition_and_backward_rejection(self):
        token = self.login("admin@test.example", "Admin1234!")
        headers = self.auth_headers(token)
        event_id = self.create_event(token, "Incident status event")
        incident = self.create_incident(token, event_id)

        investigating = self.client.patch(f"/api/v1/incidents/{incident['id']}/status", headers=headers, json={"status": "investigating", "comment": "Looking into it"})
        self.assertEqual(investigating.status_code, 200, investigating.text)
        self.assertEqual(investigating.json()["status"], "investigating")

        resolved = self.client.patch(f"/api/v1/incidents/{incident['id']}/status", headers=headers, json={"status": "resolved", "resolution": "Contained"})
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["status"], "resolved")
        self.assertEqual(resolved.json()["resolution"], "Contained")
        self.assertTrue(resolved.json()["resolved_at"])

        backward = self.client.patch(f"/api/v1/incidents/{incident['id']}/status", headers=headers, json={"status": "open"})
        self.assertEqual(backward.status_code, 422)
        self.assertEqual(backward.json()["error"]["code"], "VALIDATION_ERROR")

        fetched = self.client.get(f"/api/v1/incidents/{incident['id']}", headers=headers)
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual([update["status"] for update in fetched.json()["updates"]], ["investigating", "resolved"])

    def test_incident_map_returns_only_located_incidents(self):
        token = self.login("admin@test.example", "Admin1234!")
        headers = self.auth_headers(token)
        event_id = self.create_event(token, "Incident map event")
        located = self.create_incident(token, event_id, title="Located incident", latitude=55.75, longitude=37.61)
        self.create_incident(token, event_id, title="No coordinates incident")

        mapped = self.client.get("/api/v1/incidents/map", headers=headers)
        self.assertEqual(mapped.status_code, 200, mapped.text)
        ids = [item["id"] for item in mapped.json()]
        self.assertIn(located["id"], ids)
        for item in mapped.json():
            self.assertIsNotNone(item["latitude"])
            self.assertIsNotNone(item["longitude"])

    def test_incident_update_ownership_rbac_and_admin_delete(self):
        admin_token = self.login("admin@test.example", "Admin1234!")
        admin_headers = self.auth_headers(admin_token)
        self.create_user(admin_headers, "officer-owner@test.example", "security_officer")
        self.create_user(admin_headers, "officer-other@test.example", "security_officer")
        self.create_user(admin_headers, "rbac-viewer@test.example", "viewer")
        owner_headers = self.auth_headers(self.login("officer-owner@test.example", "User1234!"))
        other_headers = self.auth_headers(self.login("officer-other@test.example", "User1234!"))
        viewer_headers = self.auth_headers(self.login("rbac-viewer@test.example", "User1234!"))

        event_id = self.create_event(admin_token, "Incident RBAC event")

        viewer_create = self.client.post("/api/v1/incidents", headers=viewer_headers, json={"event_id": event_id, "description": "Viewer attempt"})
        self.assertEqual(viewer_create.status_code, 403)
        self.assertEqual(viewer_create.json()["error"]["code"], "FORBIDDEN")

        incident = self.create_incident(self.login("officer-owner@test.example", "User1234!"), event_id, title="Owned incident")

        updated = self.client.put(f"/api/v1/incidents/{incident['id']}", headers=owner_headers, json={"title": "Owner edit"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Owner edit")

        forbidden = self.client.put(f"/api/v1/incidents/{incident['id']}", headers=other_headers, json={"title": "Other edit"})
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["error"]["code"], "FORBIDDEN")

        delete_forbidden = self.client.delete(f"/api/v1/incidents/{incident['id']}", headers=owner_headers)
        self.assertEqual(delete_forbidden.status_code, 403)
        self.assertEqual(delete_forbidden.json()["error"]["code"], "FORBIDDEN")

        deleted = self.client.delete(f"/api/v1/incidents/{incident['id']}", headers=admin_headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)

        gone = self.client.get(f"/api/v1/incidents/{incident['id']}", headers=admin_headers)
        self.assertEqual(gone.status_code, 404)


if __name__ == "__main__":
    unittest.main()
