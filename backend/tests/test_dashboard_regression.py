import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.dependencies import get_current_user
from app.services.groq_service import generate_ai_insights

class TestDashboardRegression(unittest.TestCase):
    """
    Regression test suite verifying that GET /api/cases/{case_id}/dashboard
    remains non-blocking, safe and idempotent, and does NOT execute synchronous
    OCR or LLM synthesis on evidence upload.
    """
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.mock_user = {
            "user_id": "investigator_test",
            "role": "investigator",
            "full_name": "Test Investigator"
        }

    def setUp(self):
        # Override authentication dependency for focused router test
        app.dependency_overrides[get_current_user] = lambda: self.mock_user

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.routers.analysis.run_case_analysis")
    @patch("app.routers.analysis.get_collection")
    @patch("app.routers.analysis.verify_case_access", new_callable=AsyncMock)
    def test_dashboard_does_not_invoke_run_case_analysis_when_evidence_exists(
        self, mock_verify, mock_get_col, mock_run_analysis
    ):
        """
        Verify that GET /api/cases/{case_id}/dashboard returns fast without invoking
        run_case_analysis, even if evidence exists and no cached analysis has been run yet.
        """
        mock_verify.return_value = {
            "case_id": "CASE-REGRESS-001",
            "title": "Regression Investigation",
            "investigator": "investigator_test",
            "status": "ACTIVE"
        }

        mock_cases = MagicMock()
        mock_cases.find_one = AsyncMock(return_value={
            "case_id": "CASE-REGRESS-001",
            "title": "Regression Investigation",
            "investigator": "investigator_test",
            "status": "ACTIVE"
        })

        mock_evidence = MagicMock()
        mock_evidence.count_documents = AsyncMock(return_value=3)

        mock_analysis = MagicMock()
        mock_analysis.find_one = AsyncMock(return_value=None)  # No analysis run yet

        def col_side_effect(name):
            if name == "cases":
                return mock_cases
            elif name == "evidence":
                return mock_evidence
            elif name == "analysis":
                return mock_analysis
            return MagicMock()

        mock_get_col.side_effect = col_side_effect

        response = self.client.get("/api/cases/CASE-REGRESS-001/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Crucial assertion: run_case_analysis MUST NOT be called synchronously by GET dashboard!
        mock_run_analysis.assert_not_called()

        self.assertEqual(data["evidence_count"], 3)
        self.assertEqual(data["case_id"], "CASE-REGRESS-001")
        self.assertIn("3 evidence file(s) uploaded", data["summary"])

    def test_groq_service_client_has_timeout_and_valid_models(self):
        """
        Verify Groq client initializes with explicit timeout and excludes obsolete openai/* models.
        """
        mock_groq_init = MagicMock()
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(message=MagicMock(content='{"summary": "ok", "findings": [], "patterns": [], "leads": [], "confidence_note": "ok"}'))
        ]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_groq_init.return_value = mock_client

        with patch("app.services.groq_service.settings.GROQ_API_KEY", "gsk_test_mock_12345"), \
             patch("app.services.groq_service.settings.GROQ_MODEL", "openai/gpt-oss-120b"), \
             patch("groq.Groq", mock_groq_init):

            res = generate_ai_insights(
                case_id="CASE-REGRESS-001",
                case_title="Test",
                evidence_summary_list=[],
                entities_grouped={},
                keywords_detected=[],
                timeline_events=[],
                correlations=[]
            )

            # Check that Groq client was created with a timeout of 25s
            mock_groq_init.assert_called_with(api_key="gsk_test_mock_12345", timeout=25.0)

            # Check that create() was called with timeout=25.0 and model did not use openai/*
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            self.assertEqual(call_kwargs["timeout"], 25.0)
            self.assertFalse(call_kwargs["model"].startswith("openai/"))
            self.assertIn(call_kwargs["model"], ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"])

if __name__ == "__main__":
    unittest.main()
