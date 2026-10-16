"""
Comprehensive automated test suite for Truth Shield MVP.
Tests:
- SQLite database persistence & retrieval
- News fact-checking & linguistic heuristics
- Pillow Error Level Analysis (ELA) & OpenCV image forensics
- OpenCV video keyframe & temporal discontinuity metrics
- Flask web routes & API endpoints
"""
import os
import sys
import unittest
import json
import io

# Setup path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from app import app
from database.db import save_report, get_report, get_recent_reports, init_db, add_confirmation, get_confirmations_for_report
from services.factcheck import analyze_linguistics, verify_news_claim
from services.forensics import run_image_investigation, run_video_investigation

class TestTruthShield(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_database_lifecycle(self):
        """Tests inserting, fetching, and listing reports in SQLite."""
        report_id = save_report(
            claim_or_title="Test News Claim for DB",
            media_type="news",
            verdict="Unable to verify",
            verdict_category="unverified",
            confidence_score=35,
            summary="Test summary for verification",
            evidence_data=[{"type": "Test", "finding": "Sample finding"}],
            limitations="Sample limitations text",
            thumbnail_path=None
        )
        self.assertTrue(report_id.startswith("TS-"))
        
        # Fetch report
        report = get_report(report_id)
        self.assertIsNotNone(report)
        self.assertEqual(report["claim_or_title"], "Test News Claim for DB")
        self.assertEqual(report["verdict"], "Unable to verify")
        self.assertEqual(len(report["evidence"]), 1)
        
        # Check recent reports
        recent = get_recent_reports(limit=5)
        self.assertTrue(any(r["report_id"] == report_id for r in recent))

    def test_linguistics_analysis(self):
        """Tests sensationalism, punctuation emphasis, and capitalization detection."""
        sensational = "SHOCKING BOMBSHELL: YOU WON'T BELIEVE WHAT WAS DISCOVERED!!!"
        result = analyze_linguistics(sensational)
        self.assertTrue(result["sensationalism_detected"])
        self.assertGreater(result["capitalization_ratio"], 0.4)
        
        calm = "Local public library announces new weekend operating hours."
        calm_result = analyze_linguistics(calm)
        self.assertFalse(calm_result["sensationalism_detected"])

    def test_news_verification_fallback(self):
        """Tests that unverifiable or novel claims result in 'Unable to verify' rather than invented certainty."""
        novel_claim = "Unprecedented random obscure event happened on 99th street in 1843XYZ"
        res = verify_news_claim(novel_claim)
        self.assertEqual(res["verdict"], "Unable to verify")
        self.assertEqual(res["verdict_category"], "unverified")
        self.assertIn("limitations", res)

    def test_image_forensics_sample(self):
        """Tests Error Level Analysis and OpenCV spatial analysis on sample image."""
        auth_path = os.path.join(ROOT_DIR, "static", "samples", "authentic_photo.jpg")
        forensic_dir = os.path.join(ROOT_DIR, "uploads", "forensics")
        self.assertTrue(os.path.exists(auth_path), "Sample authentic image must exist")
        
        res = run_image_investigation(auth_path, "TEST_RUN_IMG", forensic_dir)
        self.assertIn("verdict", res)
        self.assertIn("raw_forensics", res)
        self.assertTrue(res["raw_forensics"]["ela"]["success"])
        # ELA heatmap should be saved
        ela_file = os.path.join(forensic_dir, "TEST_RUN_IMG_ela.png")
        self.assertTrue(os.path.exists(ela_file))

    def test_video_forensics_sample(self):
        """Tests OpenCV video keyframe extraction and temporal continuity."""
        vid_path = os.path.join(ROOT_DIR, "static", "samples", "sample_clip.mp4")
        forensic_dir = os.path.join(ROOT_DIR, "uploads", "forensics")
        self.assertTrue(os.path.exists(vid_path), "Sample video must exist")
        
        res = run_video_investigation(vid_path, "TEST_RUN_VID", forensic_dir)
        self.assertIn("verdict", res)
        self.assertIn("metrics", res)
        self.assertGreater(res["metrics"]["frames_analyzed"], 0)
        self.assertGreater(len(res["keyframes"]), 0)

    def test_web_routes(self):
        """Tests Flask HTTP endpoints."""
        # 1. Homepage
        r_home = self.client.get("/")
        self.assertEqual(r_home.status_code, 200)
        self.assertIn(b"Truth Shield", r_home.data)
        self.assertIn(b"News & Claim Checker", r_home.data)

        # 2. Demo News Verification
        r_demo = self.client.post("/analyze/demo", data={"sample_type": "news_mars"}, headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(r_demo.status_code, 200)
        data = json.loads(r_demo.data)
        self.assertTrue(data.get("success"))
        report_id = data.get("report_id")

        # 3. View Report Page
        r_rep = self.client.get(f"/report/{report_id}")
        self.assertEqual(r_rep.status_code, 200)
        self.assertIn(b"EVIDENCE DOSSIER", r_rep.data)

        # 4. JSON Export
        r_json = self.client.get(f"/report/{report_id}/json")
        self.assertEqual(r_json.status_code, 200)
        json_data = json.loads(r_json.data)
        self.assertEqual(json_data["report_id"], report_id)

        # 5. API Reports List
        r_api = self.client.get("/api/reports")
        self.assertEqual(r_api.status_code, 200)
        api_data = json.loads(r_api.data)
        self.assertIn("reports", api_data)

    def test_confirmation_lifecycle(self):
        """Tests adding investigator confirmations with cryptographic SHA-256 digital seals."""
        report_id = save_report(
            claim_or_title="Breaking News for Peer Audit",
            media_type="news",
            verdict="Debunked / Misleading",
            verdict_category="fake",
            confidence_score=90,
            summary="Tested claim summary",
            evidence_data=[],
            limitations="Limitations statement"
        )
        
        # Add confirmation
        conf = add_confirmation(
            report_id=report_id,
            reviewer_name="Dr. Jane Doe",
            reviewer_role="Lead OSINT Analyst",
            organization="Global Disinformation Index",
            confirmation_status="CONFIRMED_MANIPULATED",
            peer_review_notes="Verified via cross-referencing and image ELA.",
            methodology_checklist=["Primary Source Verification", "Error Level Analysis (ELA)"]
        )
        self.assertTrue(conf["confirmation_id"].startswith("CF-"))
        self.assertEqual(len(conf["digital_signature"]), 64) # SHA-256 is 64 hex characters
        
        # Verify report status was updated
        rep = get_report(report_id)
        self.assertEqual(rep["confirmation_status"], "CONFIRMED_MANIPULATED")
        self.assertEqual(len(rep["confirmations"]), 1)
        self.assertEqual(rep["confirmations"][0]["reviewer_name"], "Dr. Jane Doe")

    def test_confirmation_http_endpoints(self):
        """Tests submitting confirmation via POST and viewing the Certificate page."""
        report_id = save_report(
            claim_or_title="Test for HTTP Confirmation",
            media_type="image",
            verdict="Verified Authentic",
            verdict_category="authentic",
            confidence_score=85,
            summary="Original authentic photo",
            evidence_data=[],
            limitations="None"
        )
        
        # POST confirmation
        r_post = self.client.post(
            f"/report/{report_id}/confirm",
            data={
                "reviewer_name": "Marcus Vance",
                "reviewer_role": "Senior Photojournalist",
                "organization": "Reuters News Agency",
                "confirmation_status": "CONFIRMED_AUTHENTIC",
                "peer_review_notes": "Confirmed authentic capture from original camera RAW archive.",
                "methodology[]": ["EXIF Metadata Audit", "Error Level Analysis (ELA)"]
            },
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(r_post.status_code, 200)
        post_data = json.loads(r_post.data)
        self.assertTrue(post_data.get("success"))
        
        # View Certificate
        r_cert = self.client.get(f"/report/{report_id}/certificate")
        self.assertEqual(r_cert.status_code, 200)
        self.assertIn(b"Certificate of Verification", r_cert.data)
        self.assertIn(b"Marcus Vance", r_cert.data)

if __name__ == "__main__":
    unittest.main()
