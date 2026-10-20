import unittest
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.processors.text_extractor import extract_text_from_file
from app.processors.ocr_engine import perform_ocr

class TestOcrAndExtraction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(__file__).resolve().parent.parent.parent / "test_evidence"
        cls.temp_dir = Path(os.environ.get("TEMP", "/tmp"))

    def test_txt_extraction(self):
        txt_path = self.test_dir / "whatsapp_chat_export.txt"
        res = extract_text_from_file(str(txt_path), "whatsapp_chat_export.txt")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["extraction_method"], "plain_text")
        self.assertGreater(res["character_count"], 100)
        self.assertIn("Marcus Vance", res["extracted_text"])

    def test_native_pdf_extraction(self):
        pdf_path = self.test_dir / "security_incident_report.pdf"
        res = extract_text_from_file(str(pdf_path), "security_incident_report.pdf")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["extraction_method"], "pdf_native")
        self.assertGreater(res["character_count"], 100)
        self.assertIn("INCIDENT", res["extracted_text"])

    def test_image_ocr_png(self):
        png_path = self.test_dir / "security_alert_banner.png"
        res = extract_text_from_file(str(png_path), "security_alert_banner.png")
        self.assertEqual(res["extraction_method"], "tesseract_ocr")
        self.assertEqual(res["status"], "success")
        self.assertIn("SECURITY BREACH", res["extracted_text"])

    def test_scanned_pdf_ocr(self):
        png_path = self.test_dir / "security_alert_banner.png"
        scanned_pdf_path = self.temp_dir / "unit_test_scanned.pdf"

        # Generate a purely image-based PDF without text streams
        c = canvas.Canvas(str(scanned_pdf_path), pagesize=letter)
        c.drawImage(str(png_path), 50, 400, width=500, height=200)
        c.showPage()
        c.save()

        try:
            res = extract_text_from_file(str(scanned_pdf_path), "unit_test_scanned.pdf")
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["extraction_method"], "pdf_scanned_ocr")
            self.assertGreater(res["character_count"], 50)
            self.assertIn("SECURITY", res["extracted_text"])
        finally:
            if scanned_pdf_path.exists():
                scanned_pdf_path.unlink()

    def test_file_not_found(self):
        res = extract_text_from_file("non_existent_file.pdf", "non_existent_file.pdf")
        self.assertEqual(res["status"], "failed")
        self.assertIn("not found", res["error"].lower())

    def test_unsupported_binary_fallback(self):
        bin_path = self.temp_dir / "dummy_sample.unknown"
        with open(bin_path, "wb") as f:
            f.write(b"RAW_BINARY_FORENSIC_HEADER\x00\x01\x02FORENSIC_ARTIFACT_DATA\x00")

        try:
            res = extract_text_from_file(str(bin_path), "dummy_sample.unknown")
            self.assertEqual(res["extraction_method"], "binary_strings")
            self.assertIn("FORENSIC", res["extracted_text"])
        finally:
            if bin_path.exists():
                bin_path.unlink()

if __name__ == "__main__":
    unittest.main()
