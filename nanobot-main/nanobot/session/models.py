from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

class SessionMetadata(BaseModel):
    """
    Metadata for a session.
    Stored in metadata.json in the session directory.
    """
    id: str
    key: str = Field(description="Original session key (e.g. channel:chat_id)")
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    channel: str = "cli"
    chat_id: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)

class Message(BaseModel):
    """
    A single message in the conversation.
    Stored in the SQLite database.
    """
    id: Optional[int] = None
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    type: str = "text"  # text, summary, etc.
