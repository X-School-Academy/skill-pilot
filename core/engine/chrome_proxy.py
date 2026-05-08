"""Chrome DevTools reverse-tunnel bridge.

Two endpoints:

1. ``WS /chrome-proxy?token=<AUTH_TOKEN>`` mounted on the engine FastAPI app.
   The remote ``chrome-devtool-proxy`` Go binary (running near Chrome, behind
   NAT) dials in here and parks the connection.

2. ``WS 127.0.0.1:9223/<chrome-path>`` standalone aiohttp listener for local
   CDP clients (e.g. ``agent-browser``). On connect, the bridge pops a parked
   tunnel, sends one JSON control frame ``{"path": "<chrome-path>"}`` to it,
   then runs a transparent bidirectional relay until either side closes.

Single global session, token equals ``AUTH_TOKEN``. Bound to 127.0.0.1.
See ``extensions/chrome-devtool-proxy/remote-proxy-plan.md``.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from dataclasses import dataclass, field
from typing import Optional

from aiohttp import WSMsgType, web
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from settings import get_auth_token, logger

_DEFAULT_LISTEN_HOST = "127.0.0.1"
_DEFAULT_LISTEN_PORT = 9223
_DEFAULT_WAIT_TIMEOUT_S = 10.0


@dataclass
class _ParkedTunnel:
    ws: WebSocket
    claimed: asyncio.Event = field(default_factory=asyncio.Event)
    handoff_ready: asyncio.Event = field(default_factory=asyncio.Event)
    released: asyncio.Event = field(default_factory=asyncio.Event)


class ChromeProxyService:
    """Holds parked tunnels and runs the local 9223 listener."""

    def __init__(
        self,
        *,
        listen_host: str = _DEFAULT_LISTEN_HOST,
        listen_port: int = _DEFAULT_LISTEN_PORT,
        wait_tunnel_timeout_s: float = _DEFAULT_WAIT_TIMEOUT_S,
    ) -> None:
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._wait_timeout = wait_tunnel_timeout_s

        self._parked: list[_ParkedTunnel] = []
        self._lock = asyncio.Lock()
        self._tunnel_available = asyncio.Event()

        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.BaseSite] = None

    # ── lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", self._handle_local_root)
        app.router.add_get("/{tail:.*}", self._handle_local_ws)

        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._listen_host, self._listen_port)
        await self._site.start()
        logger.info(
            "Chrome proxy bridge listening on ws://%s:%d/",
            self._listen_host,
            self._listen_port,
        )

    async def stop(self) -> None:
        # Drop parked tunnels.
        async with self._lock:
            parked = list(self._parked)
            self._parked.clear()
        for entry in parked:
            try:
                await entry.ws.close(code=1001)
            except Exception:
                pass

        if self._site is not None:
            try:
                await self._site.stop()
            except Exception:
                pass
            self._site = None
        if self._runner is not None:
            try:
                await self._runner.cleanup()
            except Exception:
                pass
            self._runner = None
        logger.info("Chrome proxy bridge stopped")

    # ── parking side (FastAPI WS endpoint) ────────────────────────────────

    async def park_tunnel(self, websocket: WebSocket) -> None:
        """Hold the remote tunnel WS until a local client claims it or it drops.

        Caller has already accepted and authenticated the WebSocket.
        """
        entry = _ParkedTunnel(ws=websocket)
        async with self._lock:
            self._parked.append(entry)
            self._tunnel_available.set()

        peer = self._peer_repr(websocket)
        logger.info("chrome-proxy tunnel parked from %s (parked=%d)", peer, len(self._parked))

        # While parked, watch for an early disconnect from the remote. Once
        # claimed by a local client, hand the WS off entirely to the relay
        # (the relay becomes the sole reader/writer) and just wait for it to
        # signal release.
        disconnect_task = asyncio.create_task(self._wait_disconnect(websocket))
        claim_task = asyncio.create_task(entry.claimed.wait())
        try:
            done, _ = await asyncio.wait(
                {disconnect_task, claim_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if claim_task in done:
                # Stop watching the WS so the relay owns receive() exclusively.
                disconnect_task.cancel()
                try:
                    await disconnect_task
                except (asyncio.CancelledError, Exception):
                    pass
                entry.handoff_ready.set()
                # Block here until relay completes; otherwise FastAPI tears
                # down the WS as soon as this handler returns.
                await entry.released.wait()
                return
            # Disconnected before being claimed.
            claim_task.cancel()
            entry.handoff_ready.set()
        finally:
            async with self._lock:
                if entry in self._parked:
                    self._parked.remove(entry)
                if not self._parked:
                    self._tunnel_available.clear()
            logger.info("chrome-proxy tunnel released from %s", peer)

    async def _acquire_tunnel(self) -> Optional[_ParkedTunnel]:
        """Pop one idle parked tunnel, waiting up to ``wait_timeout``."""
        deadline = asyncio.get_event_loop().time() + self._wait_timeout
        while True:
            entry: Optional[_ParkedTunnel] = None
            async with self._lock:
                if self._parked:
                    entry = self._parked.pop(0)
                    if not self._parked:
                        self._tunnel_available.clear()
                    entry.claimed.set()
            if entry is not None:
                try:
                    await asyncio.wait_for(entry.handoff_ready.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    logger.warning("chrome-proxy: timed out waiting for tunnel handoff")
                    try:
                        await entry.ws.close(code=1011)
                    except Exception:
                        pass
                    return None
                return entry
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                return None
            try:
                await asyncio.wait_for(self._tunnel_available.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                return None

    # ── local listener (aiohttp on 127.0.0.1:9223) ────────────────────────

    async def _handle_local_root(self, request: web.Request) -> web.Response:
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return await self._handle_local_ws(request)
        return web.Response(text="ws proxy is running\n", content_type="text/plain")

    async def _handle_local_ws(self, request: web.Request) -> web.StreamResponse:
        if request.headers.get("Upgrade", "").lower() != "websocket":
            return web.Response(status=400, text="websocket upgrade required\n")

        path = request.rel_url.path_qs or "/"
        entry = await self._acquire_tunnel()
        if entry is None:
            logger.warning("chrome-proxy: no parked tunnel available for path=%s", path)
            return web.Response(status=503, text="no tunnel available\n")

        local_ws = web.WebSocketResponse(max_msg_size=64 * 1024 * 1024)
        try:
            await local_ws.prepare(request)
        except Exception:
            entry.released.set()
            try:
                await entry.ws.close(code=1001)
            except Exception:
                pass
            raise

        tunnel_ws = entry.ws
        try:
            try:
                await tunnel_ws.send_text(
                    json.dumps({"path": path, "headers": _request_headers(request)})
                )
            except Exception as exc:
                logger.warning("chrome-proxy: failed to send control frame: %s", exc)
                await local_ws.close(code=1011, message=b"tunnel send failed")
                try:
                    await tunnel_ws.close(code=1011)
                except Exception:
                    pass
                return local_ws

            logger.info("chrome-proxy: relay opened path=%s", path)
            await self._run_relay(local_ws, tunnel_ws)
            logger.info("chrome-proxy: relay closed path=%s", path)
            return local_ws
        finally:
            entry.released.set()

    # ── relay ─────────────────────────────────────────────────────────────

    async def _run_relay(
        self,
        local_ws: web.WebSocketResponse,
        tunnel_ws: WebSocket,
    ) -> None:
        async def local_to_tunnel() -> None:
            try:
                async for msg in local_ws:
                    if msg.type == WSMsgType.TEXT:
                        await tunnel_ws.send_text(msg.data)
                    elif msg.type == WSMsgType.BINARY:
                        await tunnel_ws.send_bytes(msg.data)
                    elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                        break
                    elif msg.type == WSMsgType.ERROR:
                        break
            except Exception as exc:
                logger.warning("chrome-proxy local->tunnel ended unexpectedly: %s", exc)

        async def tunnel_to_local() -> None:
            try:
                while True:
                    message = await tunnel_ws.receive()
                    msg_type = message.get("type")
                    if msg_type == "websocket.disconnect":
                        logger.info(
                            "chrome-proxy tunnel disconnected code=%s reason=%s",
                            message.get("code"),
                            message.get("reason"),
                        )
                        break
                    if "text" in message and message["text"] is not None:
                        await local_ws.send_str(message["text"])
                    elif "bytes" in message and message["bytes"] is not None:
                        await local_ws.send_bytes(message["bytes"])
            except WebSocketDisconnect:
                pass
            except Exception as exc:
                logger.warning("chrome-proxy tunnel->local ended unexpectedly: %s", exc)

        t1 = asyncio.create_task(local_to_tunnel())
        t2 = asyncio.create_task(tunnel_to_local())
        try:
            done, pending = await asyncio.wait(
                {t1, t2}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in pending:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            for task in done:
                try:
                    await task
                except Exception:
                    pass
        finally:
            try:
                if not local_ws.closed:
                    await local_ws.close()
            except Exception:
                pass
            try:
                if tunnel_ws.client_state != WebSocketState.DISCONNECTED:
                    await tunnel_ws.close()
            except Exception:
                pass

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    async def _wait_disconnect(websocket: WebSocket) -> None:
        """Block until the underlying WS reports disconnect."""
        try:
            while True:
                await websocket.receive()
        except WebSocketDisconnect:
            return
        except Exception:
            return

    @staticmethod
    def _peer_repr(websocket: WebSocket) -> str:
        try:
            client = websocket.client
            if client:
                return f"{client.host}:{client.port}"
        except Exception:
            pass
        return "unknown"


# ── module-level service + FastAPI route ──────────────────────────────────

_service: Optional[ChromeProxyService] = None


def _request_headers(request: web.Request) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for key in request.headers:
        headers[key] = list(request.headers.getall(key, []))
    return headers


def _read_chrome_proxy_config() -> dict:
    try:
        from settings import _SETTINGS_PATH  # type: ignore
        import json5_io as _json5

        data = _json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        services = data.get("services", {}) if isinstance(data, dict) else {}
        cfg = services.get("chrome_proxy", {}) if isinstance(services, dict) else {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def is_enabled() -> bool:
    cfg = _read_chrome_proxy_config()
    return bool(cfg.get("enabled", False))


def get_service() -> Optional[ChromeProxyService]:
    return _service


async def start_chrome_proxy() -> Optional[ChromeProxyService]:
    global _service
    if _service is not None:
        return _service
    cfg = _read_chrome_proxy_config()
    if not cfg.get("enabled", False):
        return None

    listen_host = str(cfg.get("listen_host", _DEFAULT_LISTEN_HOST))
    try:
        listen_port = int(cfg.get("listen_port", _DEFAULT_LISTEN_PORT))
    except Exception:
        listen_port = _DEFAULT_LISTEN_PORT
    try:
        wait_timeout = float(cfg.get("wait_tunnel_timeout_s", _DEFAULT_WAIT_TIMEOUT_S))
    except Exception:
        wait_timeout = _DEFAULT_WAIT_TIMEOUT_S

    svc = ChromeProxyService(
        listen_host=listen_host,
        listen_port=listen_port,
        wait_tunnel_timeout_s=wait_timeout,
    )
    await svc.start()
    _service = svc
    return svc


async def stop_chrome_proxy() -> None:
    global _service
    if _service is None:
        return
    try:
        await _service.stop()
    finally:
        _service = None


router = APIRouter()


@router.websocket("/chrome-proxy")
async def chrome_proxy_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    expected = get_auth_token().strip()
    provided = token.strip()
    if not expected or not provided or not secrets.compare_digest(expected, provided):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    svc = get_service()
    if svc is None:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
        return

    await websocket.accept()
    try:
        await svc.park_tunnel(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("chrome-proxy endpoint error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
