"""
Project SYRIN - Python API Server
轻量级封装 nanobot，提供 HTTP API 供 Electron 调用
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import asdict
from contextlib import asynccontextmanager
from datetime import datetime

# Add nanobot to path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

NANOBOT_PATH = CURRENT_DIR.parent / "nanobot-main"
sys.path.insert(0, str(NANOBOT_PATH))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from loguru import logger

# Nanobot imports
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.config.schema import Config, ExecToolConfig, TelegramConfig, DiscordConfig
from nanobot.channels.telegram import TelegramChannel
from nanobot.channels.discord import DiscordChannel
from nanobot.cron.service import CronService
from nanobot.cron.types import CronJob
from nanobot.session.manager import SessionManager

# Import custom modules
from tool_executor import ToolExecutor
from memory_store import MemoryStore
from soul_manager import SoulManager


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息")
    session_id: Optional[str] = Field(None, description="会话ID，用于保持上下文")
    system_prompt: Optional[str] = Field(None, description="系统提示词（病娇人设）")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外上下文")


class ChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str
    emotion: Optional[str] = None
    thoughts: Optional[List[str]] = None
    error: Optional[str] = None


class ToolRequest(BaseModel):
    task: str = Field(..., description="要执行的任务描述")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class SandboxRequest(BaseModel):
    code: str
    language: str = "python"


class ConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_iterations: Optional[int] = None
    emotion_enabled: Optional[bool] = None
    auto_execute: Optional[bool] = None
    enable_user_modeling: Optional[bool] = None
    brave_api_key: Optional[str] = None
    search_provider: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    discord_token: Optional[str] = None
    discord_enabled: Optional[bool] = None
    discord_allow_from: Optional[List[str]] = None
    discord_proxy: Optional[str] = None
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    proactive_enabled: Optional[bool] = None


class SystemStatus(BaseModel):
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    workspace: str
    tools_available: List[str]
    search_provider: Optional[str] = None
    telegram_connected: bool = False


# ============================================================================
# Configuration Management
# ============================================================================

class ConfigManager:
    """管理应用程序配置"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.config_file = workspace / "yandere_config.json"
        self._config = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "",
            "api_base": "",
            "max_iterations": 20,
            "emotion_enabled": True,
            "auto_execute": False,
            "enable_user_modeling": True,
            "brave_api_key": "",
            "search_provider": "brave",
            "telegram": {
                "enabled": False,
                "token": ""
            },
            "discord": {
                "enabled": False,
                "token": "",
                "allow_from": [],
                "proxy": ""
            },
            "user_name": "User",
            "role_name": "Assistant",
            "proactive_enabled": False
        }
    
    def save(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        self._config[key] = value
        self.save()
    
    def update(self, updates: Dict[str, Any]):
        # Handle nested updates for telegram
        if "telegram_token" in updates or "telegram_enabled" in updates:
            tg_config = self._config.get("telegram", {})
            if "telegram_token" in updates:
                tg_config["token"] = updates.pop("telegram_token")
            if "telegram_enabled" in updates:
                tg_config["enabled"] = updates.pop("telegram_enabled")
            self._config["telegram"] = tg_config

        if (
            "discord_token" in updates
            or "discord_enabled" in updates
            or "discord_allow_from" in updates
            or "discord_proxy" in updates
        ):
            dc_config = self._config.get("discord", {})
            if "discord_token" in updates:
                dc_config["token"] = updates.pop("discord_token")
            if "discord_enabled" in updates:
                dc_config["enabled"] = updates.pop("discord_enabled")
            if "discord_allow_from" in updates:
                dc_config["allow_from"] = updates.pop("discord_allow_from")
            if "discord_proxy" in updates:
                dc_config["proxy"] = updates.pop("discord_proxy")
            self._config["discord"] = dc_config
            
        self._config.update(updates)
        self.save()
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config.copy()


# ============================================================================
# Agent Manager
# ============================================================================

class AgentManager:
    """管理 nanobot agent 实例"""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.config_manager = ConfigManager(workspace)
        self.memory_store = MemoryStore(workspace)
        self.soul_manager = SoulManager(workspace)  # Initialize SoulManager
        self.agent: Optional[AgentLoop] = None
        self.bus = MessageBus()
        self.provider: Optional[LiteLLMProvider] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.telegram_channel: Optional[TelegramChannel] = None
        self.discord_channel: Optional[DiscordChannel] = None
        
        # Proactive Mode Services
        self.notification_queue: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self.cron_service: Optional[CronService] = None
        
        # Ensure IDENTITY.md is up-to-date
        # self.soul_manager.refresh_identity_file()
        
        self._init_agent()
    
    async def _handle_cron_job(self, job: CronJob) -> str | None:
        """Handle cron job execution."""
        logger.info(f"Executing cron job: {job.name}")
        
        if job.payload.kind == "agent_turn":
            # Send message to agent
            await self.bus.publish_inbound(InboundMessage(
                channel="notification",
                sender_id="system",
                chat_id=job.payload.to or "default",
                content=job.payload.message
            ))
            return f"Job {job.name} triggered agent turn."
            
        return None

    async def _handle_notification_outbound(self, msg: OutboundMessage) -> None:
        """Handle outbound messages from notification channel."""
        if not self.config_manager.get("proactive_enabled", False):
            return
            
        logger.info(f"Received notification outbound: {msg.content[:50]}")
        await self.notification_queue.put(msg)

    async def start(self):
        """Start all services."""
        if self.cron_service:
            await self.cron_service.start()
            logger.info("Cron service started")
            
        # Start message bus dispatcher
        asyncio.create_task(self.bus.dispatch_outbound())
        logger.info("Message bus dispatcher started")
        
        # Start agent loop
        if self.agent:
            asyncio.create_task(self.agent.run())
            logger.info("Agent loop background task started")

    def _init_agent(self):
        """初始化 agent"""
        try:
            config = self.config_manager.config
            
            # Setup provider
            provider_config = {
                "default_model": config.get("model", "gpt-4o-mini"),
                "api_key": config.get("api_key"),
            }
            
            if config.get("api_base"):
                provider_config["api_base"] = config["api_base"]
            
            self.provider = LiteLLMProvider(**provider_config)
            
            # Setup Session Manager
            self.session_manager = SessionManager(self.workspace)
            
            # Setup Cron Service
            # CronService now requires (db, session_manager, on_job)
            self.cron_service = CronService(
                self.session_manager.db, 
                self.session_manager, 
                on_job=self._handle_cron_job
            )
            
            # Setup exec config
            exec_config = ExecToolConfig(
                timeout=config.get("exec_timeout", 120),
            )
            
            # Create agent
            self.agent = AgentLoop(
                bus=self.bus,
                provider=self.provider,
                workspace=self.workspace,
                model=config.get("model"),
                max_iterations=config.get("max_iterations", 20),
                exec_config=exec_config,
                brave_api_key=config.get("brave_api_key"),
                search_provider=config.get("search_provider", "brave"),
                user_name=config.get("user_name", "User"),
                role_name=config.get("role_name", "Assistant"),
                cron_service=self.cron_service,
                session_manager=self.session_manager,
            )
            
            logger.info("Agent initialized successfully")
            
            # Subscribe to notification channel
            self.bus.subscribe_outbound("notification", self._handle_notification_outbound)
            
            # Initialize tool executor
            self.tool_executor = ToolExecutor(
                self.agent, 
                auto_execute=config.get("auto_execute", True)
            )
            logger.info("Tool executor initialized")

            # Initialize Telegram
            tg_config = config.get("telegram", {})
            if tg_config.get("enabled") and tg_config.get("token"):
                try:
                    telegram_config = TelegramConfig(
                        enabled=True,
                        token=tg_config["token"],
                        allow_from=tg_config.get("allow_from", []),
                        proxy=tg_config.get("proxy")
                    )
                    
                    self.telegram_channel = TelegramChannel(
                        config=telegram_config,
                        bus=self.bus
                    )
                    asyncio.create_task(self.telegram_channel.start())
                    logger.info("Telegram channel started")
                except Exception as e:
                    logger.error(f"Failed to start Telegram channel: {e}")

            # Initialize Discord
            dc_config = config.get("discord", {})
            if dc_config.get("enabled") and dc_config.get("token"):
                try:
                    discord_config = DiscordConfig(
                        enabled=True,
                        token=dc_config["token"],
                        allow_from=dc_config.get("allow_from", []),
                        gateway_url=dc_config.get("gateway_url", DiscordConfig().gateway_url),
                        intents=dc_config.get("intents", DiscordConfig().intents),
                        proxy_url=dc_config.get("proxy", ""),
                    )
                    self.discord_channel = DiscordChannel(
                        config=discord_config,
                        bus=self.bus
                    )
                    asyncio.create_task(self.discord_channel.start())
                    logger.info("Discord channel started")
                except Exception as e:
                    logger.error(f"Failed to start Discord channel: {e}")
            
            # Note: Background tasks are now started in start() method
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    def reload_config(self):
        """重新加载配置并重新初始化 agent"""
        # Stop existing services
        if self.telegram_channel:
            asyncio.create_task(self.telegram_channel.stop())
            self.telegram_channel = None
        if self.discord_channel:
            asyncio.create_task(self.discord_channel.stop())
            self.discord_channel = None
            
        self._init_agent()
    
    async def chat(self, message: str, session_id: Optional[str] = None, system_prompt: Optional[str] = None, background_tasks: BackgroundTasks = None) -> ChatResponse:
        """处理聊天消息 - 通过 AgentLoop 调用 (支持工具)"""
        try:
            if not self.agent:
                raise Exception("Agent not initialized")
            
            logger.info(f"Sending chat request to AgentLoop: {message[:50]}...")
            
            # 使用 AgentLoop 处理消息 (自动处理工具调用、记忆等)
            # If session_id is "default", we should check if we really want to create a new one
            # The agent loop will get_or_create. 
            # If "default" is passed, AgentLoop uses "cli:default" or similar?
            # Let's check AgentLoop.chat implementation.
            # loop.py:119: async def chat(self, content: str, session_id: str = "default") -> str:
            # loop.py:126: chat_id=session_id
            # loop.py:130: response_msg = await self._process_message(msg)
            # loop.py:157: session = self.sessions.get_or_create(msg.session_key)
            
            # If we pass "default", we get a session with key "api:default".
            # This is NOT what we want for persistent chat. We want a unique UUID.
            
            actual_session_id = session_id
            if not session_id or session_id == "default":
                # Create a new unique session for this interaction
                # This ensures the first message in "New Chat" gets a real ID
                import uuid
                actual_session_id = str(uuid.uuid4())
                logger.info(f"Created new session ID for default chat: {actual_session_id}")
            
            response_content = await self.agent.chat(
                content=message,
                session_id=actual_session_id
            )
            
            # Update soul stats
            self.soul_manager.update_stats()
            
            # Trigger background analysis (User Profiling & Sentiment)
            if background_tasks and self.config_manager.get("enable_user_modeling", True):
                # Get history from session
                session_key = actual_session_id
                
                # Better approach: Access the session directly via agent's session manager
                # Note: AgentLoop adds "api:" prefix to chat_id to form session key?
                # loop.py:122 msg = InboundMessage(channel="api", ..., chat_id=session_id)
                # loop.py: msg.session_key property -> f"{self.channel}:{self.chat_id}"
                # So the key is "api:{actual_session_id}"
                
                full_key = f"api:{actual_session_id}"
                session = self.agent.sessions.get_or_create(full_key)
                history = session.get_history(max_messages=10) # Get last 10 messages
                
                background_tasks.add_task(
                    self.soul_manager.analyze_interaction,
                    history=history,
                    provider=self.agent.provider,
                    model=self.agent.model
                )
            
            return ChatResponse(
                success=True,
                response=response_content,
                session_id=actual_session_id, # Return the REAL session ID
                emotion="normal",
                thoughts=["AgentLoop processing", "Tool execution (if needed)", "Response generation"]
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return ChatResponse(
                success=False,
                response="呜呜... 我遇到了一些问题，请稍后再试～ 🥺",
                session_id=session_id or "default",
                error=str(e)
            )
    
    async def execute_tool(self, task: str, context: Dict[str, Any]) -> ToolResponse:
        """执行工具任务 - 使用智能工具执行器或快速执行"""
        import time
        start_time = time.time()
        
        try:
            if not self.tool_executor:
                return ToolResponse(
                    success=False,
                    error="Tool executor not initialized",
                    execution_time=time.time() - start_time
                )
            
            result_data = None
            
            # 检测是否为简单命令，直接使用快速执行
            task_lower = task.lower()
            
            # 打开应用程序
            if any(keyword in task_lower for keyword in ["打开", "open", "启动"]):
                # 提取应用名称
                import re
                app_match = re.search(r'(?:打开|open|启动)\s*(?:the\s*)?(?:app\s*)?(\w+)', task_lower)
                if app_match:
                    app_name = app_match.group(1)
                    # 应用名称映射
                    app_map = {
                        "notepad": "notepad",
                        "记事本": "notepad",
                        "calc": "calc",
                        "计算器": "calc",
                        "chrome": "chrome",
                        "浏览器": "chrome",
                        "edge": "msedge",
                        "explorer": "explorer",
                        "文件管理器": "explorer",
                    }
                    
                    app_cmd = app_map.get(app_name, app_name)
                    
                    # Windows 下打开应用
                    import subprocess
                    import os
                    import sys
                    
                    try:
                        if sys.platform == "win32":
                            # 尝试多种方式打开
                            try:
                                subprocess.Popen(["cmd", "/c", "start", "", app_cmd], shell=True)
                            except:
                                subprocess.Popen(f"start {app_cmd}", shell=True)
                        else:
                            subprocess.Popen([app_cmd])
                            
                        result_data = {
                            "success": True,
                            "result": f"已帮你打开 {app_name}~ 💕",
                            "thoughts": ["检测到打开应用指令", f"执行: start {app_cmd}", "完成"]
                        }
                    except Exception as e:
                        result_data = {
                            "success": False,
                            "result": f"打开 {app_name} 失败了... 错误: {str(e)} 🥺",
                            "thoughts": ["尝试打开应用", f"错误: {str(e)}"]
                        }
            
            # 如果是简单命令已有结果，直接返回
            if result_data:
                execution_time = time.time() - start_time
                return ToolResponse(
                    success=result_data["success"],
                    result=result_data["result"],
                    execution_time=execution_time
                )
            
            # 否则使用智能工具执行器
            result = await self.tool_executor.execute_task(task, context)
            
            execution_time = time.time() - start_time
            
            return ToolResponse(
                success=result["success"],
                result=result["result"] if result["success"] else result.get("error", "Unknown error"),
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResponse(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def get_status(self) -> SystemStatus:
        """获取系统状态"""
        config = self.config_manager.config
        tools = list(self.agent.tools._tools.keys()) if self.agent else []
        
        return SystemStatus(
            status="running" if self.agent else "error",
            provider=config.get("provider"),
            model=config.get("model"),
            workspace=str(self.workspace),
            tools_available=tools
        )


# ============================================================================
# FastAPI App
# ============================================================================

# Global agent manager
agent_manager: Optional[AgentManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent_manager
    
    # Startup
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(exist_ok=True)
    
    logger.info(f"Starting Project SYRIN API Server")
    logger.info(f"Workspace: {workspace}")
    
    try:
        agent_manager = AgentManager(workspace)
        logger.info("Agent manager initialized")
        
        # Start services
        await agent_manager.start()
        
        # Subscribe to API outbound messages
        # agent_manager.bus.subscribe_outbound("api", handle_api_outbound)
        
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        agent_manager = None
    
    yield
    
    # Shutdown
    if agent_manager and agent_manager.memory_store:
        # Clean up old memories
        agent_manager.memory_store.delete_old_memories(days=30)
    
    logger.info("Shutting down Project SYRIN API Server")


app = FastAPI(
    title="Project SYRIN API",
    description="Hikari - 桌面AI伴侣 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/notifications")
async def get_notifications():
    """Get pending notifications."""
    notifications = []
    if agent_manager:
        try:
            while True:
                # Get all available notifications without blocking
                msg = agent_manager.notification_queue.get_nowait()
                notifications.append({
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat(),
                    "chat_id": msg.chat_id
                })
        except asyncio.QueueEmpty:
            pass
            
    return {"notifications": notifications}


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {
        "name": "Yandere Assistant API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """获取系统状态"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return agent_manager.get_status()


@app.get("/soul/state")
async def get_soul_state():
    """获取完整的灵魂状态（用于前端同步）"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return asdict(agent_manager.soul_manager.state)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """聊天接口"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # 1. 获取动态 System Prompt
    dynamic_system_prompt = agent_manager.soul_manager.get_current_system_prompt()
    
    # 如果请求中包含了 system_prompt (通常是前端传来的静态配置)，我们可以选择：
    # A. 忽略它，完全使用动态生成的
    # B. 拼接它
    # 这里我们选择优先使用动态生成的，如果 request 中有特殊指定的（比如调试），则覆盖
    final_system_prompt = request.system_prompt or dynamic_system_prompt
    
    # 2. 调用 Agent
    response = await agent_manager.chat(
        message=request.message,
        session_id=request.session_id,
        system_prompt=final_system_prompt,
        background_tasks=background_tasks
    )
    
    # 3. 在响应中附加当前情绪状态（供前端展示）
    response.emotion = agent_manager.soul_manager.state.emotion.primary
    
    return response


class MetricsUpdate(BaseModel):
    delta: Dict[str, float]
    reason: str = "manual_update"


@app.post("/soul/metrics")
async def update_metrics(update: MetricsUpdate):
    """手动更新关系指标 (用于测试)"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    agent_manager.soul_manager.update_metrics(update.delta, update.reason)
    return {
        "success": True, 
        "new_state": asdict(agent_manager.soul_manager.state.metrics),
        "current_phase": agent_manager.soul_manager.state.current_phase
    }


@app.get("/sessions")
async def list_sessions():
    """获取会话列表"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    raw_sessions = agent_manager.agent.sessions.list_sessions()
    sessions = []
    
    for s in raw_sessions:
        # Only expose API sessions to the frontend
        if s["id"].startswith("api:"):
            # Create a copy to avoid modifying the cache/original if it's shared
            session_data = s.copy()
            # Strip the "api:" prefix for the frontend
            session_data["id"] = s["id"][4:]
            session_data["session_id"] = s["session_id"] # Internal ID, keep as is? Or irrelevant.
            sessions.append(session_data)
            
    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Prepend api: prefix
    key = f"api:{session_id}"
    
    session = agent_manager.agent.sessions.get_or_create(key)
    return {
        "id": session_id, # Return stripped ID
        "messages": session.messages,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "metadata": session.metadata
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Prepend api: prefix
        key = f"api:{session_id}"
        
        success = agent_manager.agent.sessions.delete_session(key)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


class SessionCreate(BaseModel):
    title: Optional[str] = None


@app.post("/sessions")
async def create_session(session: SessionCreate):
    """创建新会话"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Create new UUID for the session
    import uuid
    new_uuid = str(uuid.uuid4())
    
    # Use api: prefix for the key
    key = f"api:{new_uuid}"
    
    new_session = agent_manager.agent.sessions.create_session(key=key, title=session.title)
    
    return {
        "success": True,
        "session": {
            "id": new_uuid, # Return UUID to frontend
            "title": new_session.metadata.get("title"),
            "created_at": new_session.created_at,
            "updated_at": new_session.updated_at
        }
    }


class SessionUpdate(BaseModel):
    title: Optional[str] = None


@app.patch("/sessions/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """更新会话信息"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Prepend api: prefix
    key = f"api:{session_id}"
    
    success = agent_manager.agent.sessions.update_session(key, title=update.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True}


@app.post("/execute", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """执行工具任务"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return await agent_manager.execute_tool(
        task=request.task,
        context=request.context or {}
    )


@app.post("/system/reset")
async def reset_system(confirm: bool = False):
    """
    大红按钮：删除所有本地数据（会话、记忆、配置等）。
    危险操作，需要确认！
    """
    if not confirm:
         raise HTTPException(status_code=400, detail="Please confirm deletion by setting confirm=true")
         
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
        
    try:
        import shutil
        from pathlib import Path
        
        # 1. Delete all sessions
        sessions_dir = agent_manager.workspace / "data" / "sessions"
        if sessions_dir.exists():
            # Close all active sessions first
            # (Assuming agent.sessions handles this, but we force it)
            agent_manager.agent.sessions._cache.clear()
            agent_manager.agent.sessions._index.clear()
            try:
                shutil.rmtree(sessions_dir)
            except Exception as e:
                logger.error(f"Failed to delete sessions dir: {e}")
                # Try creating it empty
        
        # Recreate empty sessions dir
        sessions_dir.mkdir(parents=True, exist_ok=True)
        # Re-init index
        (sessions_dir / "index.json").write_text("{}", encoding="utf-8")
        agent_manager.agent.sessions._load_index()
        
        # 2. Delete Memory (SQLite)
        memory_db = agent_manager.workspace / "memory" / "memories.db"
        if memory_db.exists():
            try:
                memory_db.unlink()
            except Exception as e:
                logger.error(f"Failed to delete memory db: {e}")
                
        # 3. Delete Cron Jobs
        cron_file = agent_manager.workspace / "data" / "cron" / "jobs.json"
        if cron_file.exists():
             try:
                cron_file.unlink()
             except Exception as e:
                logger.error(f"Failed to delete cron jobs: {e}")
        
        # 4. Reset User Profile/Soul
        soul_db = agent_manager.workspace / "soul_db.json"
        if soul_db.exists():
             try:
                soul_db.unlink()
             except Exception as e:
                logger.error(f"Failed to delete soul db: {e}")
                
        identity_file = agent_manager.workspace / "IDENTITY.md"
        if identity_file.exists():
             try:
                identity_file.unlink()
             except Exception as e:
                logger.error(f"Failed to delete identity file: {e}")
        
        # Reload SoulManager to reflect empty state
        agent_manager.soul_manager.state = agent_manager.soul_manager._load_state()
        agent_manager.soul_manager.refresh_identity_file()
        
        return {"success": True, "message": "All local data has been nuked."}
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")
@app.post("/sandbox/run", response_model=ToolResponse)
async def run_sandbox_code(request: SandboxRequest):
    """运行沙箱代码"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Check authorization
    config = agent_manager.config_manager.config
    if not config.get("auto_execute", True):
        return ToolResponse(
            success=False, 
            error="代码执行被阻止：自动执行已关闭。请在设置中开启'自动执行'。"
        )

    import time
    import uuid
    start_time = time.time()
    
    try:
        # 1. Prepare workspace
        sandbox_dir = agent_manager.workspace / "sandbox"
        sandbox_dir.mkdir(exist_ok=True)
        
        # 2. Write code to file
        file_ext = "py" if request.language == "python" else "txt"
        filename = f"script_{uuid.uuid4().hex[:8]}.{file_ext}"
        file_path = sandbox_dir / filename
        
        # Use WriteFileTool if available, or direct write
        # Using direct write for speed and simplicity in this specialized endpoint
        file_path.write_text(request.code, encoding="utf-8")
        
        # 3. Execute code
        if request.language in ["python", "py"]:
            # Use ExecTool to run
            exec_tool = agent_manager.agent.tools._tools.get("exec")
            if not exec_tool:
                return ToolResponse(success=False, error="Exec tool not available")
            
            # Execute relative to workspace
            cmd = f"python sandbox/{filename}"
            result = await exec_tool.execute(command=cmd)
            
            # Cleanup (optional, maybe keep for debugging?)
            # file_path.unlink(missing_ok=True)
            
            return ToolResponse(
                success=True,
                result=result,
                execution_time=time.time() - start_time
            )
        elif request.language in ["bash", "sh", "shell", "powershell", "ps1", "cmd"]:
            # Use ExecTool to run
            exec_tool = agent_manager.agent.tools._tools.get("exec")
            if not exec_tool:
                return ToolResponse(success=False, error="Exec tool not available")
            
            # On Windows, try to execute as PowerShell script if possible, or just CMD
            import sys
            if sys.platform == "win32":
                # Rename to .ps1 for better compatibility if it's generic shell
                ps1_path = file_path.with_suffix(".ps1")
                file_path.rename(ps1_path)
                cmd = f"powershell -ExecutionPolicy Bypass -File sandbox/{ps1_path.name}"
            else:
                # Unix/Linux
                cmd = f"bash sandbox/{filename}"
                
            result = await exec_tool.execute(command=cmd)
            return ToolResponse(
                success=True,
                result=result,
                execution_time=time.time() - start_time
            )
        else:
            return ToolResponse(
                success=False, 
                error=f"Unsupported language: {request.language}"
            )
            
    except Exception as e:
        return ToolResponse(
            success=False, 
            error=str(e),
            execution_time=time.time() - start_time
        )


@app.get("/config")
async def get_config():
    """获取当前配置"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # 隐藏敏感信息
    config = agent_manager.config_manager.config
    if config.get("api_key"):
        config["api_key"] = "***"
    if config.get("brave_api_key"):
        config["brave_api_key"] = "***"
    if config.get("telegram", {}).get("token"):
        config["telegram"]["token"] = "***"
    if config.get("discord", {}).get("token"):
        config["discord"]["token"] = "***"
    
    return config


@app.post("/config")
async def update_config(update: ConfigUpdate):
    """更新配置"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    updates = update.model_dump(exclude_unset=True)
    agent_manager.config_manager.update(updates)
    agent_manager.reload_config()
    
    return {"success": True, "message": "Configuration updated"}


@app.post("/telegram/test")
async def test_telegram():
    """测试 Telegram 连接"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not agent_manager.telegram_channel or not agent_manager.telegram_channel._app:
        raise HTTPException(status_code=400, detail="Telegram not connected")
    
    try:
        # Get bot info
        bot = agent_manager.telegram_channel._app.bot
        bot_info = await bot.get_me()
        
        return {
            "success": True, 
            "message": f"Connected as @{bot_info.username}",
            "bot_name": bot_info.first_name,
            "username": bot_info.username
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/tools")
async def list_tools():
    """列出可用工具"""
    if not agent_manager or not agent_manager.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    tools = []
    for name, tool in agent_manager.agent.tools._tools.items():
        tools.append({
            "name": name,
            "description": tool.description if hasattr(tool, 'description') else "",
        })
    
    return {"tools": tools}


@app.get("/memories")
async def get_memories(limit: int = 50, type_filter: Optional[str] = None):
    """获取记忆"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    memories = agent_manager.memory_store.get_recent_memories(
        limit=limit,
        type_filter=type_filter
    )
    
    return {
        "memories": [
            {
                "id": m.id,
                "timestamp": m.timestamp,
                "type": m.type,
                "content": m.content,
                "importance": m.importance
            }
            for m in memories
        ]
    }


@app.get("/memories/context")
async def get_memory_context():
    """获取记忆上下文（用于 Prompt）"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    context = agent_manager.memory_store.get_memory_context(limit=10)
    return {"context": context}


@app.post("/memories/fact")
async def add_fact(fact: str):
    """添加事实记忆"""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    memory_id = agent_manager.memory_store.add_fact(fact)
    return {"success": True, "id": memory_id}


# ============================================================================
# Main Entry
# ============================================================================

def main():
    """主入口"""
    port = int(os.environ.get("YANDERE_PORT", 8888))
    host = os.environ.get("YANDERE_HOST", "127.0.0.1")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    # Fix encoding for Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    main()
