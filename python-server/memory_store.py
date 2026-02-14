"""
长期记忆系统
使用 SQLite 存储对话历史和重要事件
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Memory:
    """记忆条目"""
    id: int
    timestamp: float
    type: str  # 'message', 'event', 'fact', 'emotion'
    content: str
    metadata: Dict[str, Any]
    importance: int  # 1-10，重要性评分


class MemoryStore:
    """长期记忆存储"""
    
    def __init__(self, workspace: Path):
        self.db_path = workspace / "yandere_memory.db"
        # Lazy initialization: Do not create DB file immediately
        # self._init_db()
    
    def _ensure_initialized(self):
        """Ensure DB is initialized before use"""
        if not self.db_path.exists():
            self._init_db()

    def _init_db(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建记忆表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    importance INTEGER DEFAULT 5
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
            
            conn.commit()
            conn.close()
            logger.info("Memory database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory database: {e}")
            raise
    
    def add_memory(
        self, 
        content: str, 
        type: str = "message", 
        metadata: Dict[str, Any] = None,
        importance: int = 5
    ) -> int:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            type: 记忆类型（message/event/fact/emotion）
            metadata: 额外元数据
            importance: 重要性（1-10）
            
        Returns:
            记忆 ID
        """
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保内容正确编码
            if isinstance(content, str):
                content = content.encode('utf-8').decode('utf-8')
            
            cursor.execute("""
                INSERT INTO memories (timestamp, type, content, metadata, importance)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().timestamp(),
                type,
                content,
                json.dumps(metadata or {}, ensure_ascii=False),
                importance
            ))
            
            memory_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.debug(f"Memory added: {type} - {content[:50]}...")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return -1
    
    def get_recent_memories(
        self, 
        limit: int = 50, 
        type_filter: Optional[str] = None
    ) -> List[Memory]:
        """获取最近的记忆"""
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if type_filter:
                cursor.execute("""
                    SELECT id, timestamp, type, content, metadata, importance
                    FROM memories
                    WHERE type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (type_filter, limit))
            else:
                cursor.execute("""
                    SELECT id, timestamp, type, content, metadata, importance
                    FROM memories
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memories.append(Memory(
                    id=row[0],
                    timestamp=row[1],
                    type=row[2],
                    content=row[3],
                    metadata=json.loads(row[4]),
                    importance=row[5]
                ))
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    def get_important_memories(self, min_importance: int = 7, limit: int = 20) -> List[Memory]:
        """获取重要记忆"""
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, type, content, metadata, importance
                FROM memories
                WHERE importance >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (min_importance, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memories.append(Memory(
                    id=row[0],
                    timestamp=row[1],
                    type=row[2],
                    content=row[3],
                    metadata=json.loads(row[4]),
                    importance=row[5]
                ))
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get important memories: {e}")
            return []
    
    def search_memories(self, keyword: str, limit: int = 20) -> List[Memory]:
        """搜索记忆"""
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, type, content, metadata, importance
                FROM memories
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{keyword}%", limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memories.append(Memory(
                    id=row[0],
                    timestamp=row[1],
                    type=row[2],
                    content=row[3],
                    metadata=json.loads(row[4]),
                    importance=row[5]
                ))
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def delete_old_memories(self, days: int = 30):
        """删除旧记忆"""
        self._ensure_initialized()
        try:
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM memories
                WHERE timestamp < ? AND importance < 7
            """, (cutoff_time,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Deleted {deleted} old memories")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete old memories: {e}")
            return 0
    
    def get_memory_context(self, limit: int = 10) -> str:
        """获取记忆上下文（用于 Prompt）"""
        memories = self.get_recent_memories(limit=limit)
        
        if not memories:
            return "这是你们的第一次对话~"
        
        context_parts = []
        for mem in reversed(memories):  # 按时间顺序
            time_str = datetime.fromtimestamp(mem.timestamp).strftime("%m-%d %H:%M")
            context_parts.append(f"[{time_str}] {mem.content}")
        
        return "\n".join(context_parts)
    
    def add_conversation(self, role: str, content: str, emotion: str = "normal"):
        """添加对话记忆"""
        metadata = {
            "role": role,
            "emotion": emotion
        }
        
        # 根据内容判断重要性
        importance = 5
        if any(word in content for word in ["喜欢", "爱", "重要", "记住"]):
            importance = 8
        elif any(word in content for word in ["讨厌", "烦", "滚"]):
            importance = 7
        
        self.add_memory(
            content=f"{role}: {content}",
            type="message",
            metadata=metadata,
            importance=importance
        )
    
    def add_fact(self, fact: str):
        """添加事实记忆"""
        self.add_memory(
            content=fact,
            type="fact",
            importance=8
        )
    
    def add_emotion_event(self, emotion: str, trigger: str):
        """添加情绪事件"""
        self.add_memory(
            content=f"情绪变化: {emotion}，触发原因: {trigger}",
            type="emotion",
            metadata={"emotion": emotion, "trigger": trigger},
            importance=6
        )
