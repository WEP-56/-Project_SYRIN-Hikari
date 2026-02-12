"""Session management for conversation history."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """
    A conversation session.
    
    Stores messages in JSONL format for easy reading and persistence.
    """
    
    key: str  # channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the session."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()
        
        # Auto-set title if it's the first user message and title is default/empty/new
        if role == "user":
            current_title = self.metadata.get("title", "")
            if not current_title or current_title == self.key or current_title == "新对话":
                # Use first 30 chars of content as title
                title = content.strip().split('\n')[0][:30]
                if len(content) > 30:
                    title += "..."
                self.metadata["title"] = title

    def get_history(self, max_messages: int = 50) -> list[dict[str, Any]]:
        """
        Get message history for LLM context.
        
        Args:
            max_messages: Maximum messages to return.
        
        Returns:
            List of messages in LLM format.
        """
        # Get recent messages
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        
        # Convert to LLM format (just role and content)
        return [{"role": m["role"], "content": m["content"]} for m in recent]
    
    def clear(self) -> None:
        """Clear all messages in the session."""
        self.messages = []
        self.updated_at = datetime.now()

    async def compact(self, provider: Any, model: str | None = None, threshold: int = 50, keep: int = 20) -> bool:
        """
        Compact the session history if it exceeds threshold.
        Summarizes older messages and keeps the most recent ones.
        """
        if len(self.messages) <= threshold:
            return False
            
        # Select messages to summarize
        to_summarize = self.messages[:-keep]
        recent = self.messages[-keep:]
        
        # Build prompt
        text_to_summarize = ""
        for msg in to_summarize:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            text_to_summarize += f"{role}: {content}\n\n"
            
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
            summary_msg = {
                "role": "system",
                "content": f"Previous conversation summary: {summary}",
                "timestamp": datetime.now().isoformat(),
                "type": "summary"
            }
            
            # Replace messages
            self.messages = [summary_msg] + recent
            self.updated_at = datetime.now()
            logger.info(f"Session {self.key} compacted. {len(to_summarize)} messages summarized.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compact session {self.key}: {e}")
            return False


class SessionManager:
    """
    Manages conversation sessions.
    
    Sessions are stored as JSONL files in the sessions directory.
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = ensure_dir(Path.home() / ".nanobot" / "sessions")
        self._cache: dict[str, Session] = {}
    
    def _get_session_path(self, key: str) -> Path:
        """Get the file path for a session."""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"
    
    def get_or_create(self, key: str) -> Session:
        """
        Get an existing session or create a new one.
        
        Args:
            key: Session key (usually channel:chat_id).
        
        Returns:
            The session.
        """
        # Check cache
        if key in self._cache:
            return self._cache[key]
        
        # Try to load from disk
        session = self._load(key)
        if session is None:
            session = Session(key=key)
        
        self._cache[key] = session
        return session
    
    async def compact_session(self, session: Session, provider: Any, model: str | None = None) -> bool:
        """Compact a session and save it."""
        if await session.compact(provider, model):
            self.save(session)
            return True
        return False
    
    def _load(self, key: str) -> Session | None:
        """Load a session from disk."""
        path = self._get_session_path(key)
        
        if not path.exists():
            return None
        
        try:
            messages = []
            metadata = {}
            created_at = None
            
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    
                    # Handle metadata (with backward compatibility)
                    if data.get("_type") == "metadata" or ("key" in data and "metadata" in data and "role" not in data):
                        metadata = data.get("metadata", {})
                        if data.get("created_at"):
                            try:
                                created_at = datetime.fromisoformat(data["created_at"])
                            except ValueError:
                                created_at = None
                    # Only add valid messages with a role
                    elif "role" in data:
                        messages.append(data)
            
            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to load session {key}: {e}")
            return None
    
    def save(self, session: Session) -> None:
        """Save a session to disk."""
        path = self._get_session_path(session.key)
        
        with open(path, "w", encoding="utf-8") as f:
            # Write metadata
            meta = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            }
            f.write(json.dumps(meta) + "\n")
            
            # Write messages
            for msg in session.messages:
                f.write(json.dumps(msg) + "\n")
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """List all available sessions sorted by update time (newest first)."""
        sessions = []
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                # Read first line for metadata
                with open(path, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    if not first_line:
                        continue
                    meta = json.loads(first_line)
                    
                    # Read last line for preview if messages exist
                    preview = ""
                    last_line = ""
                    for line in f:
                        if line.strip():
                            last_line = line
                    
                    if last_line:
                        last_msg = json.loads(last_line)
                        preview = last_msg.get("content", "")[:50]
                    
                    sessions.append({
                        "id": meta.get("key"),
                        "updated_at": meta.get("updated_at"),
                        "created_at": meta.get("created_at"),
                        "title": meta.get("metadata", {}).get("title", meta.get("key")),
                        "preview": preview
                    })
            except Exception as e:
                logger.error(f"Error reading session {path}: {e}")
        
        # Sort by updated_at descending
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete_session(self, key: str) -> bool:
        """Delete a session."""
        if key in self._cache:
            del self._cache[key]
            
        path = self._get_session_path(key)
        if path.exists():
            path.unlink()
            return True
        return False
        
    def create_session(self, key: str | None = None, title: str | None = None) -> Session:
        """Create a new session."""
        if not key:
            import uuid
            key = str(uuid.uuid4())
            
        session = Session(key=key)
        session.metadata["title"] = title or "新对话"
        session.updated_at = datetime.now()
        
        self._cache[key] = session
        self.save(session)
        return session
        
    def update_session(self, key: str, title: str | None = None) -> bool:
        """Update session metadata."""
        session = self.get_or_create(key)
        if title:
            session.metadata["title"] = title
            session.updated_at = datetime.now()
            self.save(session)
            return True
        return False
