import unittest
import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mongomock
from fastapi.testclient import TestClient

from app.config import settings
from app.database import db_manager, AsyncMongoMockDatabase
from app.main import app
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    login_rate_limiter,
)

class TestAuthAndSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure test secrets
        settings.BOOTSTRAP_SECRET_KEY = "test_bootstrap_secret_123"
        settings.JWT_SECRET_KEY = "test_jwt_secret_key_for_testing_only"
        settings.JWT_ALGORITHM = "HS256"
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = 60

        # Point db_manager to fresh in-memory mongomock
        cls.mock_client = mongomock.MongoClient()
        cls.test_db = cls.mock_client["test_cyber_investigation"]
        db_manager.db = AsyncMongoMockDatabase(cls.test_db)
        db_manager.is_live_mongo = False

        cls.client = TestClient(app)

    def setUp(self):
        # Reset collections between tests
        self.test_db["users"].drop()
        self.test_db["cases"].drop()
        self.test_db["evidence"].drop()
        self.test_db["analysis"].drop()
        self.test_db["entities"].drop()
        self.test_db["keywords"].drop()
        self.test_db["timeline"].drop()

        # Reset rate limiter
        login_rate_limiter.attempts.clear()

    # 1. Security Utilities
    def test_argon2id_password_hashing_and_verification(self):
        password = "SecureInvestigatorPassword#2026"
        hashed = hash_password(password)

        self.assertTrue(hashed.startswith("$argon2id$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword#9999", hashed))

    def test_jwt_token_creation_and_tamper_rejection(self):
        token = create_access_token({"sub": "analyst_1", "role": "investigator"})
        payload = decode_access_token(token)

        self.assertEqual(payload["sub"], "analyst_1")
        self.assertEqual(payload["role"], "investigator")
        self.assertIn("exp", payload)

        # Tampered token
        tampered_token = token[:-4] + "abcd"
        with self.assertRaises(Exception):
            decode_access_token(tampered_token)

    def test_login_rate_limiting(self):
        client_ip = "192.168.1.100"
        limiter = login_rate_limiter

        # First 4 failures do not trigger lockout
        for _ in range(4):
            limiter.record_failure(client_ip)
            limiter.check_rate_limit(client_ip)

        # 5th failure triggers lockout (429)
        limiter.record_failure(client_ip)
        with self.assertRaises(Exception) as cm:
            limiter.check_rate_limit(client_ip)
        self.assertEqual(cm.exception.status_code, 429)

        # Success clears failure count
        limiter.record_success(client_ip)
        # Should not raise now
        limiter.check_rate_limit(client_ip)

    # 2. Bootstrap & Authentication Endpoints
    def test_bootstrap_first_admin(self):
        # Missing secret header -> 403
        res = self.client.post("/api/auth/bootstrap", json={
            "user_id": "root_admin",
            "password": "AdminPassword#2026",
            "display_name": "Chief Administrator",
        })
        self.assertEqual(res.status_code, 403)

        # Wrong secret header -> 403
        res = self.client.post("/api/auth/bootstrap", json={
            "user_id": "root_admin",
            "password": "AdminPassword#2026",
            "display_name": "Chief Administrator",
        }, headers={"X-Bootstrap-Key": "wrong_secret"})
        self.assertEqual(res.status_code, 403)

        # Valid bootstrap
        res = self.client.post("/api/auth/bootstrap", json={
            "user_id": "root_admin",
            "password": "AdminPassword#2026",
            "display_name": "Chief Administrator",
        }, headers={"X-Bootstrap-Key": "test_bootstrap_secret_123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user"]["user_id"], "root_admin")
        self.assertEqual(data["user"]["role"], "admin")

        # Second attempt must be rejected (single-use)
        res2 = self.client.post("/api/auth/bootstrap", json={
            "user_id": "another_admin",
            "password": "AdminPassword#2026",
            "display_name": "Another Admin",
        }, headers={"X-Bootstrap-Key": "test_bootstrap_secret_123"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already exists", res2.json()["detail"])

    def test_login_flow_and_generic_errors(self):
        # Create an investigator
        pwd_hash = hash_password("CorrectPassword#123")
        self.test_db["users"].insert_one({
            "user_id": "detective_smith",
            "password_hash": pwd_hash,
            "role": "investigator",
            "display_name": "Detective Smith",
            "is_active": True,
        })

        # Nonexistent user -> generic 401
        res = self.client.post("/api/auth/login", json={
            "user_id": "nonexistent_user",
            "password": "SomePassword#123"
        })
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid user ID or password.")

        # Wrong password -> identical generic 401
        res = self.client.post("/api/auth/login", json={
            "user_id": "detective_smith",
            "password": "WrongPassword#999"
        })
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()["detail"], "Invalid user ID or password.")

        # Successful login
        res = self.client.post("/api/auth/login", json={
            "user_id": "detective_smith",
            "password": "CorrectPassword#123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["user_id"], "detective_smith")
        self.assertEqual(data["user"]["role"], "investigator")

        # Use token to call /api/auth/me
        token = data["access_token"]
        me_res = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["user_id"], "detective_smith")

    def test_deactivated_user_cannot_login(self):
        self.test_db["users"].insert_one({
            "user_id": "inactive_agent",
            "password_hash": hash_password("AgentSecret#123"),
            "role": "investigator",
            "display_name": "Suspended Agent",
            "is_active": False,
        })

        res = self.client.post("/api/auth/login", json={
            "user_id": "inactive_agent",
            "password": "AgentSecret#123"
        })
        self.assertEqual(res.status_code, 403)
        self.assertIn("Account is deactivated", res.json()["detail"])

    # 3. Unauthenticated Rejection across all sensitive endpoints
    def test_unauthenticated_requests_are_rejected(self):
        endpoints = [
            ("GET", "/api/cases"),
            ("POST", "/api/cases"),
            ("GET", "/api/cases/CASE-TEST-001"),
            ("DELETE", "/api/cases/CASE-TEST-001"),
            ("POST", "/api/cases/CASE-TEST-001/evidence"),
            ("GET", "/api/cases/CASE-TEST-001/evidence"),
            ("DELETE", "/api/cases/CASE-TEST-001/evidence/EV-001"),
            ("POST", "/api/cases/CASE-TEST-001/analyze"),
            ("GET", "/api/cases/CASE-TEST-001/dashboard"),
            ("GET", "/api/cases/CASE-TEST-001/report/pdf"),
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
            ("PATCH", "/api/admin/users/analyst_1"),
        ]

        for method, path in endpoints:
            if method == "GET":
                res = self.client.get(path)
            elif method == "POST":
                res = self.client.post(path)
            elif method == "DELETE":
                res = self.client.delete(path)
            elif method == "PATCH":
                res = self.client.patch(path)
            self.assertEqual(
                res.status_code, 401,
                f"Endpoint {method} {path} should return 401 for unauthenticated calls"
            )

    # 4. Role Permissions & User Administration
    def test_admin_user_management_and_safeguards(self):
        # Create an admin and an investigator
        self.test_db["users"].insert_many([
            {
                "user_id": "admin_one",
                "password_hash": hash_password("AdminPass#1"),
                "role": "admin",
                "display_name": "Admin One",
                "is_active": True,
            },
            {
                "user_id": "investigator_one",
                "password_hash": hash_password("InvPass#1"),
                "role": "investigator",
                "display_name": "Investigator One",
                "is_active": True,
            }
        ])

        admin_token = create_access_token({"sub": "admin_one", "role": "admin"})
        inv_token = create_access_token({"sub": "investigator_one", "role": "investigator"})

        # Investigator tries to list users -> 403
        res = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {inv_token}"})
        self.assertEqual(res.status_code, 403)

        # Admin lists users -> 200
        res = self.client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

        # Admin creates new user
        res = self.client.post("/api/admin/users", json={
            "user_id": "investigator_two",
            "password": "Password#456",
            "display_name": "Investigator Two",
            "role": "investigator"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 201)

        # Admin tries to deactivate the last admin -> 400 Bad Request
        res = self.client.patch("/api/admin/users/admin_one", json={
            "is_active": False
        }, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("last active", res.json()["detail"].lower())

        # Admin tries to demote the last admin to investigator -> 400 Bad Request
        res = self.client.patch("/api/admin/users/admin_one", json={
            "role": "investigator"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("last active", res.json()["detail"].lower())

        # Admin can reset password of investigator
        res = self.client.patch("/api/admin/users/investigator_two", json={
            "password": "NewSecretPassword#789"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res.status_code, 200)

        # Investigator Two can login with new password
        login_res = self.client.post("/api/auth/login", json={
            "user_id": "investigator_two",
            "password": "NewSecretPassword#789"
        })
        self.assertEqual(login_res.status_code, 200)

    # 5. Case Ownership and Cross-User Isolation
    def test_cross_user_case_isolation(self):
        self.test_db["users"].insert_many([
            {
                "user_id": "alice",
                "password_hash": hash_password("PassAlice#1"),
                "role": "investigator",
                "display_name": "Alice",
                "is_active": True,
            },
            {
                "user_id": "bob",
                "password_hash": hash_password("PassBob#2"),
                "role": "investigator",
                "display_name": "Bob",
                "is_active": True,
            },
            {
                "user_id": "chief_admin",
                "password_hash": hash_password("PassChief#3"),
                "role": "admin",
                "display_name": "Chief",
                "is_active": True,
            }
        ])

        alice_token = create_access_token({"sub": "alice", "role": "investigator"})
        bob_token = create_access_token({"sub": "bob", "role": "investigator"})
        admin_token = create_access_token({"sub": "chief_admin", "role": "admin"})

        # Alice creates a case
        create_res = self.client.post("/api/cases", json={
            "title": "Operation Red Sky",
            "investigator": "Alice Agent",
            "description": "Investigating unauthorized exfiltration"
        }, headers={"Authorization": f"Bearer {alice_token}"})
        self.assertEqual(create_res.status_code, 201)
        case_a = create_res.json()
        case_a_id = case_a["case_id"]

        # Server stamped owner_user_id to alice
        self.assertEqual(case_a["owner_user_id"], "alice")

        # Alice lists cases -> sees case_a
        alice_cases = self.client.get("/api/cases", headers={"Authorization": f"Bearer {alice_token}"}).json()
        self.assertEqual(len(alice_cases), 1)
        self.assertEqual(alice_cases[0]["case_id"], case_a_id)

        # Bob lists cases -> sees 0 cases
        bob_cases = self.client.get("/api/cases", headers={"Authorization": f"Bearer {bob_token}"}).json()
        self.assertEqual(len(bob_cases), 0)

        # Bob attempts direct access to Alice's case -> 403 Forbidden
        bob_get = self.client.get(f"/api/cases/{case_a_id}", headers={"Authorization": f"Bearer {bob_token}"})
        self.assertEqual(bob_get.status_code, 403)

        # Bob attempts to upload evidence to Alice's case -> 403 Forbidden
        bob_upload = self.client.post(
            f"/api/cases/{case_a_id}/evidence",
            files=[("files", ("evidence.txt", b"Suspicious log content", "text/plain"))],
            headers={"Authorization": f"Bearer {bob_token}"}
        )
        self.assertEqual(bob_upload.status_code, 403)

        # Bob attempts to get dashboard of Alice's case -> 403 Forbidden
        bob_dash = self.client.get(f"/api/cases/{case_a_id}/dashboard", headers={"Authorization": f"Bearer {bob_token}"})
        self.assertEqual(bob_dash.status_code, 403)

        # Bob attempts to download PDF of Alice's case -> 403 Forbidden
        bob_pdf = self.client.get(f"/api/cases/{case_a_id}/report/pdf", headers={"Authorization": f"Bearer {bob_token}"})
        self.assertEqual(bob_pdf.status_code, 403)

        # Alice attempts to delete her own case -> 403 (restricted to admin)
        alice_del = self.client.delete(f"/api/cases/{case_a_id}", headers={"Authorization": f"Bearer {alice_token}"})
        self.assertEqual(alice_del.status_code, 403)
        self.assertIn("Administrative privileges required", alice_del.json()["detail"])

        # Admin lists cases -> sees Alice's case
        admin_cases = self.client.get("/api/cases", headers={"Authorization": f"Bearer {admin_token}"}).json()
        self.assertEqual(len(admin_cases), 1)
        self.assertEqual(admin_cases[0]["case_id"], case_a_id)

        # Admin reassigns case to Bob
        reassign_res = self.client.patch(
            f"/api/admin/cases/{case_a_id}/reassign",
            json={"owner_user_id": "bob"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(reassign_res.status_code, 200)
        self.assertEqual(reassign_res.json()["owner_user_id"], "bob")

        # Now Bob has access to case_a
        bob_get_after = self.client.get(f"/api/cases/{case_a_id}", headers={"Authorization": f"Bearer {bob_token}"})
        self.assertEqual(bob_get_after.status_code, 200)

        # Alice now gets 403 Forbidden
        alice_get_after = self.client.get(f"/api/cases/{case_a_id}", headers={"Authorization": f"Bearer {alice_token}"})
        self.assertEqual(alice_get_after.status_code, 403)

        # Admin deletes case -> 204 No Content
        admin_del = self.client.delete(f"/api/cases/{case_a_id}", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(admin_del.status_code, 204)

    # 6. Legacy Unowned Cases Protection
    def test_legacy_unowned_case_protection(self):
        # Insert a legacy case with owner_user_id = None
        self.test_db["cases"].insert_one({
            "case_id": "CASE-LEGACY-001",
            "title": "Pre-Auth Incident Dossier",
            "investigator": "Unknown Legacy Investigator",
            "description": "Legacy evidence collected before authentication",
            "created_at": "2026-01-01T00:00:00",
            "owner_user_id": None
        })

        self.test_db["users"].insert_many([
            {
                "user_id": "inv_carol",
                "password_hash": hash_password("PassCarol#1"),
                "role": "investigator",
                "display_name": "Carol",
                "is_active": True,
            },
            {
                "user_id": "admin_dave",
                "password_hash": hash_password("PassDave#1"),
                "role": "admin",
                "display_name": "Dave",
                "is_active": True,
            }
        ])

        carol_token = create_access_token({"sub": "inv_carol", "role": "investigator"})
        dave_token = create_access_token({"sub": "admin_dave", "role": "admin"})

        # Carol lists cases -> does NOT see legacy case
        carol_cases = self.client.get("/api/cases", headers={"Authorization": f"Bearer {carol_token}"}).json()
        self.assertEqual(len(carol_cases), 0)

        # Carol directly accesses legacy case -> 403 Forbidden
        carol_get = self.client.get("/api/cases/CASE-LEGACY-001", headers={"Authorization": f"Bearer {carol_token}"})
        self.assertEqual(carol_get.status_code, 403)

        # Admin Dave lists cases -> sees legacy case
        dave_cases = self.client.get("/api/cases", headers={"Authorization": f"Bearer {dave_token}"}).json()
        self.assertEqual(len(dave_cases), 1)
        self.assertEqual(dave_cases[0]["case_id"], "CASE-LEGACY-001")

        # Admin Dave reassigns legacy case to Carol
        reassign_res = self.client.patch(
            "/api/admin/cases/CASE-LEGACY-001/reassign",
            json={"owner_user_id": "inv_carol"},
            headers={"Authorization": f"Bearer {dave_token}"}
        )
        self.assertEqual(reassign_res.status_code, 200)

        # Now Carol sees and can access it
        carol_cases_after = self.client.get("/api/cases", headers={"Authorization": f"Bearer {carol_token}"}).json()
        self.assertEqual(len(carol_cases_after), 1)

    # 7. Health Check Public
    def test_health_check_public_no_secrets_leaked(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        # Ensure no secrets in output
        res_str = str(data)
        self.assertNotIn("test_jwt_secret", res_str)
        self.assertNotIn("test_bootstrap_secret", res_str)

if __name__ == "__main__":
    unittest.main()
