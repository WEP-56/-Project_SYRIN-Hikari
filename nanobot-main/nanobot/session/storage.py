import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from loguru import logger

from nanobot.session.models import Message, SessionMetadata
from nanobot.utils.helpers import ensure_dir

class SessionStorage:
    """
    Manages physical storage for a single session.
    - Directory: data/sessions/<session_id>/
    - Database: messages.db (SQLite)
    - Metadata: metadata.json
    """

    def __init__(self, session_id: str, base_dir: Path):
        self.session_id = session_id
        self.base_dir = base_dir
        self.session_dir = base_dir / session_id
        self.db_path = self.session_dir / "messages.db"
        self.meta_path = self.session_dir / "metadata.json"
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """Initialize directory and database."""
        ensure_dir(self.session_dir)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT,
                timestamp TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                name TEXT,
                type TEXT DEFAULT 'text'
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"Error closing DB connection: {e}")
            finally:
                self._conn = None

    def delete(self) -> None:
        """Permanently delete the session directory."""
        self.close()
        
        # Force garbage collection to release any lingering handles
        import gc
        gc.collect()
        
        if self.session_dir.exists():
            import time
            import os
            
            # Retry loop for Windows file locks
            max_retries = 5
            for i in range(max_retries):
                try:
                    # On Windows, ignore_errors=True in rmtree often helps with readonly files,
                    # but for locked files we need to wait.
                    # We use a custom error handler to force remove readonly if needed.
                    def on_rm_error(func, path, exc_info):
                        # Attempt to fix permission error
                        try:
                            os.chmod(path, 0o777)
                            func(path)
                        except Exception:
                            # If still fails, we'll catch it in the outer loop
                            pass
                            
                    shutil.rmtree(self.session_dir, onerror=on_rm_error)
                    logger.info(f"Deleted session directory: {self.session_dir}")
                    return
                except Exception as e:
                    if i < max_retries - 1:
                        logger.warning(f"Failed to delete session dir (attempt {i+1}/{max_retries}): {e}. Retrying...")
                        time.sleep(0.5)
                    else:
                        # Final fallback: Try system command (Windows nuclear option)
                        try:
                            import subprocess
                            logger.warning(f"Using system rmdir for {self.session_dir}")
                            subprocess.run(["rmdir", "/s", "/q", str(self.session_dir)], shell=True, check=True)
                            logger.info(f"Deleted session directory using rmdir")
                            return
                        except Exception as sys_e:
                            logger.error(f"Failed to delete session directory after retries and system cmd: {self.session_dir}. Error: {e} | Sys Error: {sys_e}")

    def save_metadata(self, metadata: SessionMetadata) -> None:
        """Save session metadata to JSON."""
        with open(self.meta_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

    def load_metadata(self) -> Optional[SessionMetadata]:
        """Load session metadata from JSON."""
        if not self.meta_path.exists():
            return None
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load metadata for {self.session_id}: {e}")
            return None

    def add_message(self, message: Message) -> int:
        """Add a message to the database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Serialize tool_calls if present
        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = json.dumps(message.tool_calls)

        cursor.execute("""
            INSERT INTO messages (role, content, timestamp, tool_calls, tool_call_id, name, type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message.role,
            message.content,
            message.timestamp.isoformat(),
            tool_calls_json,
            message.tool_call_id,
            message.name,
            message.type
        ))
        conn.commit()
        return cursor.lastrowid

    def get_messages(self, limit: int = 1000) -> List[Message]:
        """Get messages from the database."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM messages ORDER BY id ASC LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        messages = []
        for row in rows:
            tool_calls = None
            if row["tool_calls"]:
                try:
                    tool_calls = json.loads(row["tool_calls"])
                except:
                    pass
            
            messages.append(Message(
                id=row["id"],
                role=row["role"],
                content=row["content"] or "",
                timestamp=datetime.fromisoformat(row["timestamp"]),
                tool_calls=tool_calls,
                tool_call_id=row["tool_call_id"],
                name=row["name"],
                type=row["type"]
            ))
        return messages

    def clear_messages(self) -> None:
        """Clear all messages (truncate table)."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages")
        conn.commit()

    def replace_messages(self, messages: List[Message]) -> None:
        """Replace all messages (transactional)."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM messages")
            for msg in messages:
                tool_calls_json = json.dumps(msg.tool_calls) if msg.tool_calls else None
                cursor.execute("""
                    INSERT INTO messages (role, content, timestamp, tool_calls, tool_call_id, name, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    tool_calls_json,
                    msg.tool_call_id,
                    msg.name,
                    msg.type
                ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
