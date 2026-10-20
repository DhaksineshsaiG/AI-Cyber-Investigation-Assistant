import unittest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.nlp_service import extract_entities_from_text
from app.services.keyword_service import detect_suspicious_keywords
from app.services.timeline_service import extract_timeline_events
from app.services.correlation_service import correlate_cross_evidence

class TestForensicServices(unittest.TestCase):
    def test_nlp_entity_extraction(self):
        sample_text = """
        Incident Memo: Suspect John Doe was observed logging in from 192.168.1.50 on 2026-07-15.
        He contacted j.doe@darksec.org and placed an encrypted call to +1 415 555 0199.
        Target was Apex Global Defense Corp.
        """
        res = extract_entities_from_text(sample_text, "memo.txt")
        grouped = res["grouped"]

        # Check IP
        self.assertIn("192.168.1.50", grouped["IP & System Addresses"])
        # Check Email
        self.assertIn("j.doe@darksec.org", grouped["Email Addresses"])
        # Check Phone
        self.assertTrue(any("415" in p for p in grouped["Phone Numbers"]))
        # Check Date
        self.assertTrue(any("2026" in d for d in grouped["Dates"]))

    def test_nlp_empty_input(self):
        res = extract_entities_from_text("", "empty.txt")
        self.assertEqual(len(res["all_entities"]), 0)
        self.assertEqual(len(res["grouped"]["Names"]), 0)

    def test_keyword_detection(self):
        text = "The intruder used an admin override to bypass authentication, then attempted to wipe the logs."
        matches = detect_suspicious_keywords(text, "server.log")
        keywords_found = [m["keyword"] for m in matches]

        self.assertIn("admin override", keywords_found)
        self.assertIn("bypass", keywords_found)
        self.assertIn("wipe", keywords_found)

        # Check severity
        for m in matches:
            if m["keyword"] in ["admin override", "wipe", "bypass"]:
                self.assertEqual(m["severity"], "high")

    def test_keyword_empty_text(self):
        matches = detect_suspicious_keywords("", "empty.txt")
        self.assertEqual(matches, [])

    def test_timeline_extraction(self):
        chat_text = """
        [2026-06-14 09:42:00] Alice: I am exporting the customer database now.
        [2026-06-14 09:46:00] Bob: Make sure to delete the server logs immediately.
        [2026-06-15 11:00:00] Alice: Logs wiped successfully.
        """
        events = extract_timeline_events(chat_text, "chat.txt")
        self.assertGreaterEqual(len(events), 2)
        # Verify chronological ordering
        for i in range(len(events) - 1):
            t1 = events[i]["date_iso"]
            t2 = events[i + 1]["date_iso"]
            self.assertLessEqual(t1, t2)

        # Verify high-risk tag for 'delete' or 'wiped'
        wipe_event = next((e for e in events if "wipe" in e["detail"].lower() or "delete" in e["detail"].lower()), None)
        self.assertIsNotNone(wipe_event)

    def test_correlation_multi_source(self):
        ev1 = {
            "filename": "chat.txt",
            "entities": [{"type": "PERSON", "value": "Elena Rostova"}, {"type": "IP_ADDRESS", "value": "10.0.0.1"}],
            "keywords": [{"keyword": "wipe", "severity": "high", "count": 2}]
        }
        ev2 = {
            "filename": "memo.pdf",
            "entities": [{"type": "PERSON", "value": "Elena Rostova"}, {"type": "EMAIL", "value": "elena@corp.com"}],
            "keywords": [{"keyword": "wipe", "severity": "high", "count": 1}]
        }
        correlations = correlate_cross_evidence([ev1, ev2])

        # Person Elena Rostova should be correlated across 2 files
        person_corr = next((c for c in correlations if c["entity_value"] == "Elena Rostova"), None)
        self.assertIsNotNone(person_corr)
        self.assertEqual(len(person_corr["evidence_names"]), 2)
        self.assertIn("chat.txt", person_corr["evidence_names"])
        self.assertIn("memo.pdf", person_corr["evidence_names"])

        # Keyword 'wipe' should also be correlated across 2 files
        wipe_corr = next((c for c in correlations if c["entity_value"] == "wipe"), None)
        self.assertIsNotNone(wipe_corr)
        self.assertEqual(len(wipe_corr["evidence_names"]), 2)

if __name__ == "__main__":
    unittest.main()
