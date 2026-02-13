import sqlite3
import json
import time
from pathlib import Path
from typing import List, Optional, Any
from loguru import logger
from .models import SessionModel, CronJobModel

class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._connect() as conn:
            # Sessions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    title TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    meta_json TEXT DEFAULT '{}'
                )
            """)
            
            # Cron Jobs Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cron_jobs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    name TEXT,
                    schedule_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    next_run_at INTEGER,
                    enabled BOOLEAN DEFAULT 1,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    # --- Session Operations ---

    def get_session(self, key: str) -> Optional[SessionModel]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE key = ?", (key,)).fetchone()
            if row:
                return SessionModel(*row)
        return None

    def create_session(self, session: SessionModel):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, key, title, created_at, updated_at, meta_json) VALUES (?, ?, ?, ?, ?, ?)",
                (session.id, session.key, session.title, session.created_at, session.updated_at, session.meta_json)
            )
            conn.commit()

    def update_session(self, session: SessionModel):
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET title=?, updated_at=?, meta_json=? WHERE id=?",
                (session.title, session.updated_at, session.meta_json, session.id)
            )
            conn.commit()

    def delete_session(self, key: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def list_sessions(self) -> List[SessionModel]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
            return [SessionModel(*row) for row in rows]

    # --- Cron Operations ---

    def get_job(self, job_id: str) -> Optional[CronJobModel]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM cron_jobs WHERE id = ?", (job_id,)).fetchone()
            if row:
                return CronJobModel(*row)
        return None

    def list_jobs(self, session_id: Optional[str] = None) -> List[CronJobModel]:
        with self._connect() as conn:
            if session_id:
                rows = conn.execute("SELECT * FROM cron_jobs WHERE session_id = ?", (session_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM cron_jobs").fetchall()
            return [CronJobModel(*row) for row in rows]
            
    def get_due_jobs(self, now_ms: int) -> List[CronJobModel]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM cron_jobs WHERE enabled = 1 AND next_run_at <= ?", 
                (now_ms,)
            ).fetchall()
            return [CronJobModel(*row) for row in rows]

    def create_job(self, job: CronJobModel):
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO cron_jobs 
                   (id, session_id, name, schedule_json, payload_json, next_run_at, enabled, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job.id, job.session_id, job.name, job.schedule_json, job.payload_json, 
                 job.next_run_at, job.enabled, job.created_at, job.updated_at)
            )
            conn.commit()

    def update_job(self, job: CronJobModel):
        with self._connect() as conn:
            conn.execute(
                """UPDATE cron_jobs 
                   SET name=?, schedule_json=?, payload_json=?, next_run_at=?, enabled=?, updated_at=? 
                   WHERE id=?""",
                (job.name, job.schedule_json, job.payload_json, job.next_run_at, 
                 job.enabled, job.updated_at, job.id)
            )
            conn.commit()

    def delete_job(self, job_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0
