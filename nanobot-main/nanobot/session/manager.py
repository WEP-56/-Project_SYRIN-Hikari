"""Session management using SQLite for metadata and directory-based storage for messages."""

import json
import uuid
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

from nanobot.utils.helpers import ensure_dir
from nanobot.session.models import Message, SessionMetadata
from nanobot.session.storage import SessionStorage
from nanobot.storage.db import Database
from nanobot.storage.models import SessionModel

class Session:
    """
    A conversation session proxy.
    Wraps SessionStorage (messages) and SessionModel (metadata).
    """

    def __init__(self, storage: SessionStorage, model: SessionModel, db: Database):
        self._storage = storage
        self._model = model
        self._db = db
        self.is_processing = False  # Busy Guard flag

    def close(self) -> None:
        """Close the underlying storage connection."""
        self._storage.close()

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def key(self) -> str:
        return self._model.key

    @property
    def created_at(self) -> datetime:
        return datetime.fromtimestamp(self._model.created_at / 1000)

    @property
    def updated_at(self) -> datetime:
        return datetime.fromtimestamp(self._model.updated_at / 1000)
    
    @updated_at.setter
    def updated_at(self, value: datetime):
        self._model.updated_at = int(value.timestamp() * 1000)
        self._db.update_session(self._model)

    @property
    def title(self) -> str:
        return self._model.title

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Return metadata dict for compatibility.
        Includes core fields (id, key, title) and extra metadata.
        """
        base = {
            "id": self._model.id,
            "key": self._model.key,
            "title": self._model.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        base.update(self._model.metadata)
        return base
    
    @property
    def messages(self) -> List[Dict[str, Any]]:
        """
        Legacy property for accessing messages. 
        Returns dict representation of all messages.
        Use get_history() for LLM context.
        """
        msgs = self._storage.get_messages(limit=10000)
        return [self._msg_to_dict(m) for m in msgs]
    
    @messages.setter
    def messages(self, value: List[Dict[str, Any]]):
        """
        Legacy setter for messages.
        WARNING: This replaces ALL messages in the DB.
        """
        new_msgs = []
        for m in value:
            new_msgs.append(Message(
                role=m.get("role", "unknown"),
                content=m.get("content", ""),
                timestamp=datetime.fromisoformat(m["timestamp"]) if "timestamp" in m else datetime.now(),
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name"),
                type=m.get("type", "text")
            ))
        self._storage.replace_messages(new_msgs)

    def _msg_to_dict(self, m: Message) -> Dict[str, Any]:
        d = {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat()
        }
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.name:
            d["name"] = m.name
        if m.type != "text":
            d["type"] = m.type
        return d

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the session."""
        msg = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            **kwargs
        )
        self._storage.add_message(msg)
        
        # Update timestamp
        self.updated_at = datetime.now()
        
        # Auto-set title if it's the first user message and title is default
        if role == "user":
            current_title = self._model.title
            if not current_title or current_title == "New Chat" or current_title == "新对话":
                # Use first 30 chars of content as title
                title = content.strip().split('\n')[0][:30]
                if len(content) > 30:
                    title += "..."
                self._model.title = title
                self._db.update_session(self._model)

    def get_history(self, max_messages: int = 50) -> List[Dict[str, Any]]:
        """
        Get message history for LLM context.
        """
        # Get sufficient messages from DB
        msgs = self._storage.get_messages(limit=max_messages * 2)
        
        # Return last N messages converted to dicts
        recent = msgs[-max_messages:] if len(msgs) > max_messages else msgs
        return [self._msg_to_dict(m) for m in recent]

    async def compact(self, provider: Any, model: str | None = None, threshold: int = 50, keep: int = 20) -> bool:
        """
        Compact the session history if it exceeds threshold.
        """
        all_msgs = self._storage.get_messages(limit=10000)
        if len(all_msgs) <= threshold:
            return False
            
        # Select messages to summarize
        to_summarize = all_msgs[:-keep]
        recent = all_msgs[-keep:]
        
        # Build prompt
        text_to_summarize = ""
        for msg in to_summarize:
            text_to_summarize += f"{msg.role}: {msg.content}\n\n"
            
        prompt = f"""Please summarize the following conversation history into a concise paragraph. 
Focus on key facts, user preferences, and important decisions. 
Do not lose critical information.

Conversation:
{text_to_summarize}

Summary:"""

        try:
            # Generate summary
            summary = await provider.generate(prompt, system="You are a helpful assistant summarizing a conversation.", model=model)
            
            # Create summary message
            summary_msg = Message(
                role="system",
                content=f"Previous conversation summary: {summary}",
                timestamp=datetime.now(),
                type="summary"
            )
            
            # Replace messages in DB
            self._storage.replace_messages([summary_msg] + recent)
            
            self.updated_at = datetime.now()
            logger.info(f"Session {self.key} compacted. {len(to_summarize)} messages summarized.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compact session {self.key}: {e}")
            return False


class SessionManager:
    """
    Manages conversation sessions using SQLite (metadata) and SessionStorage (messages).
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_root = ensure_dir(workspace / "data" / "sessions")
        self.db_path = workspace / "data" / "global.db"
        self.db = Database(self.db_path)
        self._cache: Dict[str, Session] = {}

    def get_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by UUID."""
        # 1. Check cache (by scanning values, expensive but okay for small N)
        for s in self._cache.values():
            if s.id == session_id:
                return s
                
        # 2. Check DB
        # We need a method in DB to get by ID, but currently we only have get_session(key).
        # Let's list all or add a method. For now, let's iterate.
        # Ideally we should add get_session_by_id to Database.
        # But wait, our get_session uses KEY. 
        # Let's rely on listing for now or add the method.
        # Actually, let's use list_sessions and filter.
        all_sessions = self.db.list_sessions()
        model = next((s for s in all_sessions if s.id == session_id), None)
        
        if model:
            return self._load_session(model)
        return None

    def get_or_create(self, key: str) -> Session:
        """
        Get an existing session or create a new one.
        
        Args:
            key: Session key (usually channel:chat_id).
        """
        # 1. Check memory cache
        if key in self._cache:
            return self._cache[key]

        # 2. Check DB
        model = self.db.get_session(key)
        
        if model:
            # Load existing
            session = self._load_session(model)
            if session:
                self._cache[key] = session
                return session
            else:
                # Session data corrupt/missing
                self.db.delete_session(key)

        # 3. Create new
        return self.create_session(key)

    def _load_session(self, model: SessionModel) -> Optional[Session]:
        """Load session from storage."""
        storage = SessionStorage(model.id, self.sessions_root)
        try:
            storage.initialize()
            return Session(storage, model, self.db)
        except Exception as e:
            logger.error(f"Failed to load session {model.id}: {e}")
            return None

    def create_session(self, key: str | None = None, title: str | None = None) -> Session:
        """Create a new session."""
        if not key:
            key = str(uuid.uuid4())
            
        # Enforce Isolation: If session exists for this key, delete it first.
        existing = self.db.get_session(key)
        if existing:
            logger.info(f"Session collision for {key}. Deleting old session {existing.id}...")
            self.delete_session(key)
            
        # Generate new session ID
        session_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        
        # Create storage (fs + messages.db)
        storage = SessionStorage(session_id, self.sessions_root)
        storage.initialize()
        
        # Create metadata model
        model = SessionModel(
            id=session_id,
            key=key,
            title=title or "New Chat",
            created_at=now_ms,
            updated_at=now_ms,
            meta_json="{}"
        )
        
        # Save to DB
        self.db.create_session(model)
        
        # Create session object
        session = Session(storage, model, self.db)
        self._cache[key] = session
        
        logger.info(f"Created new session {session_id} for key {key}")
        return session

    def delete_session(self, key: str) -> bool:
        """Delete a session completely."""
        # 1. Remove from memory cache
        if key in self._cache:
            self._cache[key].close()
            del self._cache[key]
            
        # 2. Get info from DB
        model = self.db.get_session(key)
        if not model:
            return False
            
        # 3. Delete storage (files)
        storage = SessionStorage(model.id, self.sessions_root)
        storage.delete()
        
        # 4. Delete from DB
        self.db.delete_session(key)
        
        logger.info(f"Deleted session {key} ({model.id})")
        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions."""
        models = self.db.list_sessions()
        sessions = []
        
        for model in models:
            # We peek into storage for preview without fully loading Session object
            # to avoid opening too many DB connections.
            storage = SessionStorage(model.id, self.sessions_root)
            preview = ""
            try:
                msgs = storage.get_messages(limit=1) # Get last one? No, get_messages sorts by ID ASC.
                # To get last message efficiently we might need descending sort in storage, 
                # but currently get_messages gets first N.
                # Let's just get all (limit 1000) and take last.
                # Optimization: Add get_last_message to SessionStorage.
                msgs = storage.get_messages(limit=1000)
                if msgs:
                    preview = msgs[-1].content[:50]
            except Exception:
                pass
            finally:
                storage.close()

            sessions.append({
                "id": model.key, # Use key as ID for frontend compatibility
                "session_id": model.id, # Internal ID
                "updated_at": datetime.fromtimestamp(model.updated_at / 1000).isoformat(),
                "created_at": datetime.fromtimestamp(model.created_at / 1000).isoformat(),
                "title": model.title,
                "preview": preview
            })
            
        return sessions

    async def compact_session(self, session: Session, provider: Any, model: str | None = None) -> bool:
        """Compact a session and save it."""
        return await session.compact(provider, model)

    def save(self, session: Session) -> None:
        """
        Save session. No-op in new architecture as changes are persisted immediately.
        """
        pass

    def update_session(self, key: str, title: str | None = None) -> bool:
        """Update session metadata."""
        session = self.get_or_create(key)
        if title:
            session._model.title = title
            session.updated_at = datetime.now() # Trigger save
            return True
        return False
