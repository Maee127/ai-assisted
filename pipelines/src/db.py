"""
Database layer for the Instagram lead pipeline.
Three-stage design: raw_comments (source of truth, never edited) ->
processed_comments (classification results) -> validated_leads
(only high-confidence records copied here for outreach review).
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "./data/leads.db")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "365"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    comment_text TEXT NOT NULL,
    comment_hash TEXT NOT NULL UNIQUE,
    source_page TEXT,
    post_url TEXT,
    ig_media_id TEXT,
    ig_media_owner_id TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'own_media',
    comment_created_at TEXT,
    collected_at TEXT NOT NULL,
    raw_payload TEXT,
    processing_status TEXT DEFAULT 'pending'
        CHECK (processing_status IN
            ('pending','processed','rejected','duplicate','processing_error'))
);

CREATE TABLE IF NOT EXISTS processed_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_comment_id INTEGER NOT NULL UNIQUE,
    cleaned_text TEXT,
    detected_language TEXT,
    is_question INTEGER,
    is_relevant INTEGER,
    intent_type TEXT,
    product_category TEXT,
    confidence_score REAL,
    classifier_stage TEXT,  -- 'rules' | 'ai'
    validation_status TEXT DEFAULT 'unreviewed'
        CHECK (validation_status IN
            ('unreviewed','validated','rejected','needs_review')),
    processed_at TEXT,
    FOREIGN KEY (raw_comment_id) REFERENCES raw_comments(id)
);

CREATE TABLE IF NOT EXISTS validated_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_comment_id INTEGER NOT NULL UNIQUE,
    username TEXT NOT NULL,
    original_comment TEXT NOT NULL,
    cleaned_question TEXT,
    intent_type TEXT,
    product_category TEXT,
    lead_score REAL,
    source_page TEXT,
    post_url TEXT,
    lawful_basis TEXT NOT NULL DEFAULT 'legitimate_interest',
    consent_status TEXT DEFAULT 'implicit_public_comment',
    validated_at TEXT NOT NULL,
    retention_expires_at TEXT NOT NULL,
    status TEXT DEFAULT 'new',
    FOREIGN KEY (raw_comment_id) REFERENCES raw_comments(id)
);

CREATE TABLE IF NOT EXISTS erasure_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ig_username TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    fulfilled_at TEXT,
    scope TEXT DEFAULT 'all'
);

CREATE INDEX IF NOT EXISTS idx_raw_status ON raw_comments(processing_status);
CREATE INDEX IF NOT EXISTS idx_processed_status ON processed_comments(validation_status);
CREATE INDEX IF NOT EXISTS idx_leads_retention ON validated_leads(retention_expires_at);
"""


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def hash_comment(username: str, post_id: str, text: str) -> str:
    normalized = f"{normalize_username(username)}|{post_id or ''}|{(text or '').strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def insert_raw_comment(record: dict) -> dict:
    """Insert a raw comment. Returns {'inserted': True, 'id': ...} or
    {'inserted': False, 'reason': 'duplicate'}. Never raises on duplicates."""
    conn = get_connection()
    comment_hash = hash_comment(
        record.get("username"), record.get("ig_media_id"), record.get("comment_text")
    )
    try:
        cur = conn.execute(
            """
            INSERT INTO raw_comments (
                username, comment_text, comment_hash, source_page, post_url,
                ig_media_id, ig_media_owner_id, source_type,
                comment_created_at, collected_at, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalize_username(record.get("username")),
                record.get("comment_text"),
                comment_hash,
                record.get("source_page"),
                record.get("post_url"),
                record.get("ig_media_id"),
                record.get("ig_media_owner_id"),
                record.get("source_type", "own_media"),
                record.get("comment_created_at"),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(record.get("raw_payload", {})),
            ),
        )
        conn.commit()
        return {"inserted": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        return {"inserted": False, "reason": "duplicate"}
    finally:
        conn.close()


def retention_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS)).isoformat()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")