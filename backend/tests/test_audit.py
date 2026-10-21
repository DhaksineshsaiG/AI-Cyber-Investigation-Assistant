import unittest
import io
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_collection, db_manager, AsyncMongoMockDatabase
from app.utils.security import create_access_token, hash_password
from app.services.audit_service import record_audit_event
import mongomock

class TestAuditMonitoring(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_client = mongomock.MongoClient()
        cls.test_db = cls.mock_client["test_cyber_investigation_audit"]
        db_manager.db = AsyncMongoMockDatabase(cls.test_db)
        db_manager.is_live_mongo = False

    def setUp(self):
        self.client = TestClient(app)
        self.admin_user = {
            "user_id": "audit_admin",
            "display_name": "Audit Administrator",
            "role": "admin",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }
        self.investigator_user = {
            "user_id": "audit_investigator",
            "display_name": "Field Investigator One",
            "role": "investigator",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }
        self.other_investigator = {
            "user_id": "audit_investigator_two",
            "display_name": "Field Investigator Two",
            "role": "investigator",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }

        self.admin_token = create_access_token({
            "sub": self.admin_user["user_id"],
            "role": self.admin_user["role"],
            "display_name": self.admin_user["display_name"]
        })
        self.investigator_token = create_access_token({
            "sub": self.investigator_user["user_id"],
            "role": self.investigator_user["role"],
            "display_name": self.investigator_user["display_name"]
        })

    async def asyncSetUp(self):
        users_col = get_collection("users")
        audit_col = get_collection("audit_events")
        cases_col = get_collection("cases")
        evidence_col = get_collection("evidence")

        await users_col.delete_many({})
        await audit_col.delete_many({})
        await cases_col.delete_many({})
        await evidence_col.delete_many({})

        # Insert test users
        admin_doc = dict(self.admin_user, password_hash=hash_password("admin_pass123"))
        inv_doc = dict(self.investigator_user, password_hash=hash_password("inv_pass123"))
        inv2_doc = dict(self.other_investigator, password_hash=hash_password("inv2_pass123"))

        await users_col.insert_many([admin_doc, inv_doc, inv2_doc])

    def test_unauthenticated_audit_access_blocked(self):
        """Unauthenticated requests to audit endpoints must return 401."""
        res_events = self.client.get("/api/admin/audit/events")
        self.assertEqual(res_events.status_code, 401)

        res_summary = self.client.get("/api/admin/audit/summary")
        self.assertEqual(res_summary.status_code, 401)

        res_pdf = self.client.get("/api/admin/audit/report/pdf")
        self.assertEqual(res_pdf.status_code, 401)

    def test_investigator_audit_access_forbidden(self):
        """Investigators must NEVER be able to query admin audit endpoints (403 Forbidden)."""
        headers = {"Authorization": f"Bearer {self.investigator_token}"}

        res_events = self.client.get("/api/admin/audit/events", headers=headers)
        self.assertEqual(res_events.status_code, 403)

        res_summary = self.client.get("/api/admin/audit/summary", headers=headers)
        self.assertEqual(res_summary.status_code, 403)

        res_pdf = self.client.get("/api/admin/audit/report/pdf", headers=headers)
        self.assertEqual(res_pdf.status_code, 403)

    async def test_admin_query_audit_events_and_filtering(self):
        """Admin can retrieve audit events and filter by investigator, action type, and search."""
        # Record sample events for two different investigators
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="investigation_created",
            action_label="Created an investigation",
            case_id="CASE-001",
            details="Created case for unauthorized intrusion",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="evidence_uploaded",
            action_label="Uploaded an evidence file",
            case_id="CASE-001",
            details="Uploaded evidence 'firewall_logs.txt'",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator_two",
            actor_role="investigator",
            action_type="investigation_created",
            action_label="Created an investigation",
            case_id="CASE-002",
            details="Created case for phishing attack",
            status="success"
        )

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        # 1. Query all events
        res = self.client.get("/api/admin/audit/events", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_count"], 3)
        self.assertEqual(len(data["events"]), 3)

        # 2. Filter by investigator_id
        res_inv = self.client.get("/api/admin/audit/events?investigator_id=audit_investigator", headers=headers)
        self.assertEqual(res_inv.status_code, 200)
        data_inv = res_inv.json()
        self.assertEqual(data_inv["total_count"], 2)
        for ev in data_inv["events"]:
            self.assertEqual(ev["actor_user_id"], "audit_investigator")

        # 3. Filter by action_type
        res_act = self.client.get("/api/admin/audit/events?action_type=evidence_uploaded", headers=headers)
        self.assertEqual(res_act.status_code, 200)
        data_act = res_act.json()
        self.assertEqual(data_act["total_count"], 1)
        self.assertEqual(data_act["events"][0]["action_type"], "evidence_uploaded")

        # 4. Search filter
        res_search = self.client.get("/api/admin/audit/events?search=phishing", headers=headers)
        self.assertEqual(res_search.status_code, 200)
        data_search = res_search.json()
        self.assertEqual(data_search["total_count"], 1)
        self.assertEqual(data_search["events"][0]["case_id"], "CASE-002")

    async def test_audit_summary_calculation(self):
        """Admin audit summary must calculate accurate counts from real recorded events."""
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="investigation_created",
            action_label="Created an investigation",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="evidence_uploaded",
            action_label="Uploaded an evidence file",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="analysis_completed",
            action_label="Started evidence analysis",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="report_downloaded",
            action_label="Generated investigation report",
            status="success"
        )
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="access_denied",
            action_label="Access denied",
            status="failure"
        )

        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/api/admin/audit/summary?investigator_id=audit_investigator", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_activities"], 5)
        self.assertEqual(data["investigations_created"], 1)
        self.assertEqual(data["evidence_uploaded"], 1)
        self.assertEqual(data["analysis_runs"], 1)
        self.assertEqual(data["reports_downloaded"], 1)
        self.assertEqual(data["failed_operations"], 1)

    async def test_audit_pdf_report_download(self):
        """Admin can download formal PDF audit report."""
        await record_audit_event(
            actor_user_id="audit_investigator",
            actor_role="investigator",
            action_type="investigation_created",
            action_label="Created an investigation",
            case_id="CASE-RPT-01",
            details="Created test case for PDF export",
            status="success"
        )

        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/api/admin/audit/report/pdf?investigator_id=audit_investigator", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    async def test_workflow_events_logged_automatically(self):
        """Evidence upload and case creation must log real audit events automatically."""
        headers = {"Authorization": f"Bearer {self.investigator_token}"}

        # 1. Create case via standard API
        res_case = self.client.post("/api/cases", json={
            "title": "Incident Auto Audit Case",
            "description": "Verifying automatic audit log creation"
        }, headers=headers)
        self.assertEqual(res_case.status_code, 201)
        case_id = res_case.json()["case_id"]

        # 2. Upload evidence file
        sample_file = io.BytesIO(b"timestamp=2026-01-01 suspicious outbound packet to 198.51.100.25")
        res_ev = self.client.post(
            f"/api/cases/{case_id}/evidence",
            files=[("files", ("network_log.txt", sample_file, "text/plain"))],
            headers=headers
        )
        self.assertEqual(res_ev.status_code, 201)

        # 3. Verify audit events recorded in database
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res_audit = self.client.get(f"/api/admin/audit/events?case_id={case_id}", headers=admin_headers)
        self.assertEqual(res_audit.status_code, 200)
        events = res_audit.json()["events"]

        action_types = [e["action_type"] for e in events]
        self.assertIn("investigation_created", action_types)
        self.assertIn("evidence_uploaded", action_types)

        # Verify actor user ID is strictly the authenticated investigator
        for e in events:
            self.assertEqual(e["actor_user_id"], "audit_investigator")
