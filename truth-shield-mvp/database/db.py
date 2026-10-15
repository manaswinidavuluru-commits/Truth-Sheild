"""
Database module for Truth Shield MVP.
Manages SQLite storage for investigation reports and verification records.
"""
import os
import sqlite3
import json
import uuid
from datetime import datetime

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATABASE_DIR, "truth_shield.db")

def get_connection():
    """Returns a connection to the SQLite database with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE NOT NULL,
                claim_or_title TEXT NOT NULL,
                media_type TEXT NOT NULL,
                verdict TEXT NOT NULL,
                verdict_category TEXT NOT NULL,
                confidence_score INTEGER,
                summary TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                limitations TEXT NOT NULL,
                thumbnail_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Index for fast lookups by report_id and recent records
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_report_id ON reports(report_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC)")
        conn.commit()

def save_report(claim_or_title, media_type, verdict, verdict_category, confidence_score, summary, evidence_data, limitations, thumbnail_path=None):
    """
    Saves a new verification report to the database.
    Returns the generated report_id.
    """
    report_id = f"TS-{uuid.uuid4().hex[:8].upper()}"
    evidence_json = json.dumps(evidence_data, ensure_ascii=False)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (
                report_id, claim_or_title, media_type, verdict,
                verdict_category, confidence_score, summary,
                evidence_json, limitations, thumbnail_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, claim_or_title, media_type, verdict,
            verdict_category, confidence_score, summary,
            evidence_json, limitations, thumbnail_path
        ))
        conn.commit()
    return report_id

def get_report(report_id):
    """Retrieves a single report by its unique report_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        report = dict(row)
        try:
            report['evidence'] = json.loads(report['evidence_json'])
        except Exception:
            report['evidence'] = []
        return report

def get_recent_reports(limit=10):
    """Retrieves the most recent reports."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, report_id, claim_or_title, media_type, verdict,
                   verdict_category, confidence_score, summary, thumbnail_path, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# Auto-initialize when imported
init_db()
