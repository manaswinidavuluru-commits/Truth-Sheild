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
from database.db import save_report, get_report, get_recent_reports, init_db
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

if __name__ == "__main__":
    unittest.main()
