"""
Soul Manager - The core of the Project SYRIN Soul Engine.
Manages global state, affection system, and dynamic persona generation.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger
import sys

# Add nanobot to path if not already there
NANOBOT_PATH = Path(__file__).parent.parent / "nanobot-main"
if str(NANOBOT_PATH) not in sys.path:
    sys.path.insert(0, str(NANOBOT_PATH))

from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.bus.events import InboundMessage, OutboundMessage
from prompt_layers import (
    PromptLayerStack, 
    RelationshipMetrics, 
    EmotionState, 
    UserProfile, 
    EventMemory,
    PHASE_TEMPLATES
)

@dataclass
class SoulState:
    """完整的灵魂状态"""
    # L2: 关系指标
    metrics: RelationshipMetrics = field(default_factory=RelationshipMetrics)
    
    # 情绪状态
    emotion: EmotionState = field(default_factory=EmotionState)
    
    # L3: 用户画像
    user_profile: UserProfile = field(default_factory=UserProfile)
    
    # L4: 事件记忆
    event_memories: List[EventMemory] = field(default_factory=list)
    
    # 统计数据
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_conversations": 0,
        "last_interaction": None,
        "phase_transitions": []
    })
    
    # 当前阶段 (1/2/3)
    current_phase: int = 1

class SoulManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.db_path = workspace / "soul_db.json"
        self.identity_file = workspace / "IDENTITY.md"
        
        self.prompt_stack = PromptLayerStack(workspace)
        self.state = self._load_state()
        
    def _load_state(self) -> SoulState:
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding='utf-8'))
                
                # 尝试加载新版数据结构
                if "metrics" in data:
                    metrics = RelationshipMetrics(**data.get("metrics", {}))
                    emotion = EmotionState(**data.get("emotion", {}))
                    user_profile = UserProfile(**data.get("user_profile", {}))
                    
                    # 处理 EventMemory 列表
                    memories_data = data.get("event_memories", [])
                    event_memories = [EventMemory(**m) for m in memories_data]
                    
                    stats = data.get("stats", {})
                    current_phase = data.get("current_phase", 1)
                    
                    return SoulState(
                        metrics=metrics,
                        emotion=emotion,
                        user_profile=user_profile,
                        event_memories=event_memories,
                        stats=stats,
                        current_phase=current_phase
                    )
                else:
                    # 迁移旧版数据 (简单的 affection score -> metrics)
                    logger.info("Migrating legacy soul state...")
                    old_score = data.get("affection", {}).get("score", 0)
                    metrics = RelationshipMetrics(
                        affection=old_score,
                        trust=old_score * 0.8,  # 粗略估算
                        dependency=old_score * 0.5
                    )
                    user_profile = UserProfile(
                        name=data.get("user_profile", {}).get("name", "User"),
                        facts=data.get("user_profile", {}).get("facts", {})
                    )
                    return SoulState(metrics=metrics, user_profile=user_profile)
                    
            except Exception as e:
                logger.error(f"Failed to load soul DB: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Default state
        return SoulState()
    
    def save(self):
        """Save current state to DB."""
        try:
            # Helper to convert dataclasses to dict recursively
            data = asdict(self.state)
            self.db_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save soul DB: {e}")

    def get_current_system_prompt(self) -> str:
        """获取当前生成的完整 System Prompt"""
        # 1. 确定当前阶段
        phase = self.state.metrics.get_phase()
        
        # 如果阶段发生变化，记录并在 state 中更新
        if phase != self.state.current_phase:
            logger.info(f"Phase transition: {self.state.current_phase} -> {phase}")
            self.state.current_phase = phase
            self.state.stats["phase_transitions"].append({
                "timestamp": datetime.now().isoformat(),
                "from": self.state.current_phase,
                "to": phase
            })
            self.save()
            
        # 2. 生成 Prompt
        prompt = self.prompt_stack.generate_full_prompt(
            phase=phase,
            metrics=self.state.metrics,
            emotion=self.state.emotion,
            profile=self.state.user_profile,
            event_memories=self.state.event_memories
        )
        
        # 3. 同步写入 IDENTITY.md (供其他工具或参考使用)
        try:
            self.identity_file.write_text(prompt, encoding='utf-8')
        except Exception:
            pass
            
        return prompt

    def refresh_identity_file(self):
        """Refreshes the IDENTITY.md file (alias for get_current_system_prompt)"""
        self.get_current_system_prompt()

    def update_metrics(self, delta_metrics: Dict[str, float], reason: str = "interaction"):
        """更新关系指标"""
        metrics = self.state.metrics
        
        for key, delta in delta_metrics.items():
            if hasattr(metrics, key):
                current_val = getattr(metrics, key)
                new_val = max(0.0, min(100.0, current_val + delta))
                setattr(metrics, key, new_val)
        
        self.save()
        logger.info(f"Updated metrics ({reason}): {delta_metrics}")

    def update_stats(self):
        """Update interaction stats."""
        self.state.stats["total_conversations"] += 1
        self.state.stats["last_interaction"] = datetime.now().isoformat()
        self.save()

    async def analyze_interaction(self, history: List[Dict[str, Any]], provider: LiteLLMProvider, model: str):
        """
        分析交互，提取用户画像信息和情感波动
        """
        if not history or len(history) < 2:
            return

        # Use last few messages for analysis
        recent_msgs = history[-6:]
        conversation_text = ""
        for msg in recent_msgs:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        prompt = f"""
Analyze the conversation between User and Assistant.
Extract User Profile info and assess the impact on their Relationship.

Conversation:
{conversation_text}

Output JSON only:
{{
  "user_facts": {{ "key": "value" }},     // New facts about user (name, preferences, etc.)
  "user_interest_topics": ["topic1"],     // Topics user seems interested in
  "interaction_style": "casual",          // casual/formal/playful/aggressive
  "sentiment_impact": {{                  // Impact on relationship metrics (-5.0 to +5.0)
    "affection": 0.0,
    "trust": 0.0,
    "possessiveness": 0.0,                // Did user make assistant jealous?
    "dependency": 0.0,                    // Did user help or rely on assistant?
    "intimacy": 0.0
  }},
  "assistant_emotion": {{                 // Assistant's likely emotional reaction
    "primary": "neutral",                 // happy/excited/clingy/jealous/anxious/sad/angry/obsessive
    "intensity": 0.5                      // 0.0 to 1.0
  }},
  "significant_event": "..."              // If something important happened, describe it briefly. Else null.
}}
"""
        
        try:
            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                tools=[],
                model=model
            )
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            result = json.loads(content)
            
            # 1. Update User Profile
            updated_profile = False
            new_facts = result.get("user_facts", {})
            for k, v in new_facts.items():
                if k not in self.state.user_profile.facts:
                    self.state.user_profile.facts[k] = v
                    updated_profile = True
            
            if "interaction_style" in result:
                self.state.user_profile.interaction_style = result["interaction_style"]
                updated_profile = True
                
            if "user_interest_topics" in result:
                for topic in result["user_interest_topics"]:
                    if topic not in self.state.user_profile.topics_of_interest:
                        self.state.user_profile.topics_of_interest.append(topic)
                        updated_profile = True
            
            # 2. Update Metrics
            impact = result.get("sentiment_impact", {})
            if impact:
                self.update_metrics(impact, reason="interaction_analysis")
            
            # 3. Update Emotion
            emo_data = result.get("assistant_emotion", {})
            if emo_data:
                self.state.emotion.primary = emo_data.get("primary", "neutral")
                self.state.emotion.intensity = float(emo_data.get("intensity", 0.5))
                updated_profile = True
                
            # 4. Record Significant Event
            event_desc = result.get("significant_event")
            if event_desc:
                new_event = EventMemory(
                    timestamp=datetime.now().isoformat(),
                    event_type="interaction",
                    description=event_desc,
                    importance=3  # Default importance
                )
                self.state.event_memories.append(new_event)
                updated_profile = True

            if updated_profile:
                self.save()
                
        except Exception as e:
            logger.error(f"Failed to analyze interaction: {e}")
