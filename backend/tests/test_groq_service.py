import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.groq_service import generate_ai_insights

class TestGroqService(unittest.TestCase):
    def test_offline_fallback_when_no_api_key(self):
        with patch("app.services.groq_service.settings.GROQ_API_KEY", ""):
            res = generate_ai_insights(
                case_id="CASE-TEST-001",
                case_title="Test Case",
                evidence_summary_list=[{"filename": "test.txt", "size": 100, "sha256": "abc", "text": "sample text"}],
                entities_grouped={"Names": ["Alice"]},
                keywords_detected=[{"keyword": "breach", "category": "Incident", "severity": "high", "count": 1}],
                timeline_events=[{"time": "12:00", "title": "Event", "detail": "Detail", "source_evidence": "test.txt"}],
                correlations=[]
            )
            self.assertIn("summary", res)
            self.assertIn("findings", res)
            self.assertIn("patterns", res)
            self.assertIn("leads", res)
            self.assertIn("confidence_note", res)
            self.assertFalse(res["is_available"])
            self.assertIn("offline", res["summary"].lower())

    def test_online_groq_mock_response(self):
        mock_groq_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content='''{
                        "summary": "Mocked analysis summary of unauthorized activity.",
                        "findings": ["Evidence file test.txt contains unauthorized access record."],
                        "patterns": ["Rapid data egress observed."],
                        "leads": ["Cross-reference Alice against user directory."],
                        "confidence_note": "Grounded on 1 evidence source"
                    }'''
                )
            )
        ]
        mock_groq_client.chat.completions.create.return_value = mock_completion

        with patch("app.services.groq_service.settings.GROQ_API_KEY", "gsk_dummy_test_key_12345"), \
             patch("groq.Groq", return_value=mock_groq_client):
            res = generate_ai_insights(
                case_id="CASE-TEST-001",
                case_title="Test Case",
                evidence_summary_list=[{"filename": "test.txt", "size": 100, "sha256": "abc", "text": "sample text"}],
                entities_grouped={"Names": ["Alice"]},
                keywords_detected=[{"keyword": "breach", "category": "Incident", "severity": "high", "count": 1}],
                timeline_events=[{"time": "12:00", "title": "Event", "detail": "Detail", "source_evidence": "test.txt"}],
                correlations=[]
            )
            self.assertTrue(res["is_available"])
            self.assertEqual(res["summary"], "Mocked analysis summary of unauthorized activity.")
            self.assertEqual(len(res["findings"]), 1)
            self.assertEqual(len(res["leads"]), 1)
            self.assertEqual(res["confidence_note"], "Grounded on 1 evidence source")

if __name__ == "__main__":
    unittest.main()
