"""Discord channel implementation using Discord Gateway websocket."""

import asyncio
import inspect
import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets
from loguru import logger
from python_socks.async_.asyncio import Proxy

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import DiscordConfig


DISCORD_API_BASE = "https://discord.com/api/v10"
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 20MB


class DiscordChannel(BaseChannel):
    """Discord channel using Gateway websocket."""

    name = "discord"

    def __init__(self, config: DiscordConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: DiscordConfig = config
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._seq: int | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._typing_tasks: dict[str, asyncio.Task] = {}
        self._http: httpx.AsyncClient | None = None
        self._proxy_url: str | None = None

    async def start(self) -> None:
        """Start the Discord gateway connection."""
        if not self.config.token:
            logger.error("Discord bot token not configured")
            return

        self._running = True
        self._proxy_url = (
            self.config.proxy_url
            or os.environ.get("DISCORD_PROXY")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )
        client_kwargs: dict[str, Any] = {"timeout": 30.0}
        if self._proxy_url:
            logger.info(f"Discord proxy enabled: {self._proxy_url}")
            params = inspect.signature(httpx.AsyncClient).parameters
            if "proxy" in params:
                client_kwargs["proxy"] = self._proxy_url
            elif "proxies" in params:
                client_kwargs["proxies"] = self._proxy_url
            else:
                logger.warning("httpx client proxy not supported in this version; REST calls will be direct")
                client_kwargs["trust_env"] = False

        self._http = httpx.AsyncClient(**client_kwargs)
        await self._preflight_check()

        while self._running:
            try:
                logger.info("Connecting to Discord gateway...")
                connect_kwargs = dict(
                    open_timeout=15,
                    close_timeout=5,
                    ping_interval=20,
                    ping_timeout=20,
                )
                if self._proxy_url:
                    params = inspect.signature(websockets.connect).parameters
                    if "proxy" in params:
                        connect_kwargs["proxy"] = self._proxy_url
                    else:
                        if "sock" in params:
                            proxy_socket = await self._connect_proxy_socket()
                            if proxy_socket:
                                connect_kwargs["sock"] = proxy_socket
                        else:
                            logger.warning("websockets client proxy not supported in this version")

                async with websockets.connect(self.config.gateway_url, **connect_kwargs) as ws:
                    self._ws = ws
                    await self._gateway_loop()
            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(
                    f"Discord gateway closed: code={e.code} reason={e.reason}"
                )
                if e.code == 4014:
                    logger.error(
                        "Discord privileged intents not enabled for this bot. "
                        "Enable MESSAGE CONTENT intent in the Developer Portal or reduce intents."
                    )
            except TimeoutError:
                logger.warning(
                    "Discord gateway timeout during connect or heartbeat. "
                    "This usually means the gateway is unreachable or blocked."
                )
            except Exception as e:
                logger.warning(f"Discord gateway error: {type(e).__name__}: {e}")
                if self._running:
                    logger.info("Reconnecting to Discord gateway in 5 seconds...")
                    await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the Discord channel."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        for task in self._typing_tasks.values():
            task.cancel()
        self._typing_tasks.clear()
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Discord REST API."""
        if not self._http:
            logger.warning("Discord HTTP client not initialized")
            return

        url = f"{DISCORD_API_BASE}/channels/{msg.chat_id}/messages"
        payload: dict[str, Any] = {"content": msg.content}

        if msg.reply_to:
            payload["message_reference"] = {"message_id": msg.reply_to}
            payload["allowed_mentions"] = {"replied_user": False}

        headers = {"Authorization": f"Bot {self.config.token}"}

        try:
            for attempt in range(3):
                try:
                    response = await self._http.post(url, headers=headers, json=payload)
                    if response.status_code == 429:
                        data = response.json()
                        retry_after = float(data.get("retry_after", 1.0))
                        logger.warning(f"Discord rate limited, retrying in {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    return
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Error sending Discord message: {e}")
                    else:
                        await asyncio.sleep(1)
        finally:
            await self._stop_typing(msg.chat_id)

    async def _preflight_check(self) -> None:
        if not self._http:
            return

        headers = {"Authorization": f"Bot {self.config.token}"}
        try:
            response = await self._http.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
            if response.status_code == 401:
                logger.error("Discord token unauthorized. Check that you used Bot Token.")
                return
            if response.status_code == 403:
                logger.error("Discord token forbidden. Check bot permissions and token scope.")
                return
            response.raise_for_status()
            data = response.json()
            username = data.get("username")
            bot_id = data.get("id")
            logger.info(f"Discord token OK: {username} ({bot_id})")
        except Exception as e:
            logger.warning(f"Discord preflight failed: {type(e).__name__}: {e}")

        await self._probe_gateway_connectivity()

    async def _probe_gateway_connectivity(self) -> None:
        if self._proxy_url:
            logger.info("Discord gateway probe skipped due to proxy configuration")
            return

        parsed = urlparse(self.config.gateway_url)
        host = parsed.hostname or "gateway.discord.gg"
        port = parsed.port or 443

        try:
            addrs = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
            targets = {addr[4][0] for addr in addrs}
            logger.info(f"Discord gateway DNS OK: {host} -> {', '.join(sorted(targets))}")
        except Exception as e:
            logger.warning(f"Discord gateway DNS failed: {type(e).__name__}: {e}")
            return

        try:
            await asyncio.to_thread(socket.create_connection, (host, port), 5)
            logger.info(f"Discord gateway TCP OK: {host}:{port}")
        except Exception as e:
            logger.warning(f"Discord gateway TCP failed: {type(e).__name__}: {e}")

    async def _connect_proxy_socket(self):
        try:
            parsed = urlparse(self.config.gateway_url)
            host = parsed.hostname or "gateway.discord.gg"
            port = parsed.port or 443
            proxy = Proxy.from_url(self._proxy_url)
            return await proxy.connect(dest_host=host, dest_port=port)
        except Exception as e:
            logger.warning(f"Discord proxy socket failed: {type(e).__name__}: {e}")
            return None

    async def _gateway_loop(self) -> None:
        """Main gateway loop: identify, heartbeat, dispatch events."""
        if not self._ws:
            return

        async for raw in self._ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from Discord gateway: {raw[:100]}")
                continue

            op = data.get("op")
            event_type = data.get("t")
            seq = data.get("s")
            payload = data.get("d")

            if seq is not None:
                self._seq = seq

            if op == 10:
                # HELLO: start heartbeat and identify
                interval_ms = payload.get("heartbeat_interval", 45000)
                await self._start_heartbeat(interval_ms / 1000)
                await self._identify()
            elif op == 0 and event_type == "READY":
                logger.info("Discord gateway READY")
            elif op == 0 and event_type == "MESSAGE_CREATE":
                await self._handle_message_create(payload)
            elif op == 7:
                # RECONNECT: exit loop to reconnect
                logger.info("Discord gateway requested reconnect")
                break
            elif op == 9:
                # INVALID_SESSION: reconnect
                logger.warning("Discord gateway invalid session")
                break

    async def _identify(self) -> None:
        """Send IDENTIFY payload."""
        if not self._ws:
            return

        identify = {
            "op": 2,
            "d": {
                "token": self.config.token,
                "intents": self.config.intents,
                "properties": {
                    "os": "nanobot",
                    "browser": "nanobot",
                    "device": "nanobot",
                },
            },
        }
        await self._ws.send(json.dumps(identify))

    async def _start_heartbeat(self, interval_s: float) -> None:
        """Start or restart the heartbeat loop."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        async def heartbeat_loop() -> None:
            while self._running and self._ws:
                payload = {"op": 1, "d": self._seq}
                try:
                    await self._ws.send(json.dumps(payload))
                except Exception as e:
                    logger.warning(f"Discord heartbeat failed: {e}")
                    break
                await asyncio.sleep(interval_s)

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def _handle_message_create(self, payload: dict[str, Any]) -> None:
        """Handle incoming Discord messages."""
        author = payload.get("author") or {}
        if author.get("bot"):
            return

        sender_id = str(author.get("id", ""))
        channel_id = str(payload.get("channel_id", ""))
        content = payload.get("content") or ""

        if not sender_id or not channel_id:
            return

        if not self.is_allowed(sender_id):
            return

        content_parts = [content] if content else []
        media_paths: list[str] = []
        media_dir = Path.home() / ".nanobot" / "media"

        for attachment in payload.get("attachments") or []:
            url = attachment.get("url")
            filename = attachment.get("filename") or "attachment"
            size = attachment.get("size") or 0
            if not url or not self._http:
                continue
            if size and size > MAX_ATTACHMENT_BYTES:
                content_parts.append(f"[attachment: {filename} - too large]")
                continue
            try:
                media_dir.mkdir(parents=True, exist_ok=True)
                file_path = media_dir / f"{attachment.get('id', 'file')}_{filename.replace('/', '_')}"
                resp = await self._http.get(url)
                resp.raise_for_status()
                file_path.write_bytes(resp.content)
                media_paths.append(str(file_path))
                content_parts.append(f"[attachment: {file_path}]")
            except Exception as e:
                logger.warning(f"Failed to download Discord attachment: {e}")
                content_parts.append(f"[attachment: {filename} - download failed]")

        reply_to = (payload.get("referenced_message") or {}).get("id")

        await self._start_typing(channel_id)

        await self._handle_message(
            sender_id=sender_id,
            chat_id=channel_id,
            content="\n".join(p for p in content_parts if p) or "[empty message]",
            media=media_paths,
            metadata={
                "message_id": str(payload.get("id", "")),
                "guild_id": payload.get("guild_id"),
                "reply_to": reply_to,
            },
        )

    async def _start_typing(self, channel_id: str) -> None:
        """Start periodic typing indicator for a channel."""
        await self._stop_typing(channel_id)

        async def typing_loop() -> None:
            url = f"{DISCORD_API_BASE}/channels/{channel_id}/typing"
            headers = {"Authorization": f"Bot {self.config.token}"}
            while self._running:
                try:
                    await self._http.post(url, headers=headers)
                except Exception:
                    pass
                await asyncio.sleep(8)

        self._typing_tasks[channel_id] = asyncio.create_task(typing_loop())

    async def _stop_typing(self, channel_id: str) -> None:
        """Stop typing indicator for a channel."""
        task = self._typing_tasks.pop(channel_id, None)
        if task:
            task.cancel()
