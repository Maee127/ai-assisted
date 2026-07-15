import sqlite3
import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._init_database()
    
    def _get_connection(self):
        """Get a database connection with proper settings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode and foreign keys
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        
        return conn
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            # Create tables
            conn.executescript("""
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
            """)
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """Normalize username to lowercase and trim"""
        return (username or "").strip().lower()
    
    @staticmethod
    def hash_comment(username: str, post_id: str, text: str) -> str:
        """Generate SHA256 hash for deduplication"""
        normalized = f"{Database.normalize_username(username)}|{post_id or ''}|{(text or '').strip().lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def insert_raw_comment(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a raw comment row.
        Returns {'inserted': True, 'id': id} on success,
        or {'inserted': False, 'reason': 'duplicate'} if already seen.
        """
        comment_hash = self.hash_comment(
            record.get('username', ''),
            record.get('ig_media_id', ''),
            record.get('comment_text', '')
        )
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO raw_comments (
                        username, comment_text, comment_hash, source_page, post_url,
                        ig_media_id, ig_media_owner_id, source_type,
                        comment_created_at, collected_at, raw_payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.normalize_username(record.get('username', '')),
                    record.get('comment_text', ''),
                    comment_hash,
                    record.get('source_page'),
                    record.get('post_url'),
                    record.get('ig_media_id'),
                    record.get('ig_media_owner_id'),
                    record.get('source_type', 'own_media'),
                    record.get('comment_created_at'),
                    datetime.now().isoformat(),
                    json.dumps(record.get('raw_payload', {}))
                ))
                
                return {'inserted': True, 'id': cursor.lastrowid}
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                return {'inserted': False, 'reason': 'duplicate'}
            raise