"""
Database module for Truth Shield MVP.
Manages SQLite storage for investigation reports, verification records,
and peer investigator confirmation reviews.
"""
import os
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime

DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATABASE_DIR, "truth_shield.db")

def get_connection():
    """Returns a connection to the SQLite database with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes and migrates the database schema."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Reports table
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
                confirmation_status TEXT DEFAULT 'PENDING',
                confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Safely migrate existing reports table if confirmation columns don't exist yet
        cursor.execute("PRAGMA table_info(reports)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "confirmation_status" not in columns:
            cursor.execute("ALTER TABLE reports ADD COLUMN confirmation_status TEXT DEFAULT 'PENDING'")
        if "confirmed_at" not in columns:
            cursor.execute("ALTER TABLE reports ADD COLUMN confirmed_at TIMESTAMP")
            
        # 2. Peer Investigator Confirmations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confirmation_id TEXT UNIQUE NOT NULL,
                report_id TEXT NOT NULL,
                reviewer_name TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                organization TEXT,
                confirmation_status TEXT NOT NULL,
                peer_review_notes TEXT NOT NULL,
                methodology_checklist TEXT,
                digital_signature TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (report_id) REFERENCES reports(report_id)
            )
        """)
        
        # Indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_report_id ON reports(report_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confirmations_report_id ON confirmations(report_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confirmations_created ON confirmations(created_at DESC)")
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
                evidence_json, limitations, thumbnail_path, confirmation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            report_id, claim_or_title, media_type, verdict,
            verdict_category, confidence_score, summary,
            evidence_json, limitations, thumbnail_path
        ))
        conn.commit()
    return report_id

def add_confirmation(report_id, reviewer_name, reviewer_role, organization, confirmation_status, peer_review_notes, methodology_checklist=None):
    """
    Adds a peer investigator confirmation review to a report.
    Generates a cryptographic SHA-256 digital signature to seal the verification record.
    Updates the parent report's confirmation_status.
    """
    confirmation_id = f"CF-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.utcnow().isoformat()
    
    # Generate cryptographic tamper-evident signature
    sig_payload = f"{confirmation_id}:{report_id}:{reviewer_name}:{confirmation_status}:{now_iso}"
    digital_signature = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()
    
    checklist_str = json.dumps(methodology_checklist or [], ensure_ascii=False)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO confirmations (
                confirmation_id, report_id, reviewer_name, reviewer_role,
                organization, confirmation_status, peer_review_notes,
                methodology_checklist, digital_signature, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            confirmation_id, report_id, reviewer_name, reviewer_role,
            organization, confirmation_status, peer_review_notes,
            checklist_str, digital_signature, now_iso
        ))
        
        # Update report status
        cursor.execute("""
            UPDATE reports
            SET confirmation_status = ?, confirmed_at = ?
            WHERE report_id = ?
        """, (confirmation_status, now_iso, report_id))
        conn.commit()
        
    return {
        "confirmation_id": confirmation_id,
        "digital_signature": digital_signature,
        "confirmed_at": now_iso
    }

def get_confirmations_for_report(report_id):
    """Retrieves all peer investigator confirmations for a specific report."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM confirmations
            WHERE report_id = ?
            ORDER BY created_at DESC
        """, (report_id,))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            try:
                item["checklist"] = json.loads(item["methodology_checklist"])
            except Exception:
                item["checklist"] = []
            results.append(item)
        return results

def get_report(report_id):
    """Retrieves a single report by its unique report_id, including its peer confirmations."""
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
            
        # Attach confirmations
        report['confirmations'] = get_confirmations_for_report(report_id)
        return report

def get_recent_reports(limit=10):
    """Retrieves the most recent reports with confirmation status."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, report_id, claim_or_title, media_type, verdict,
                   verdict_category, confidence_score, summary, thumbnail_path,
                   confirmation_status, confirmed_at, created_at
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# Auto-initialize when imported
init_db()
