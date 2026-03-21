from pathlib import Path
import re
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from mcp_servers.mcp_to_skills.service import MCPBridgeSocketService
from routes import router, start_heartbeat_watcher, _cleanup_webui_tmux_sessions, cleanup_stale_workflow_session
from scheduler import load_schedules, start_scheduler, stop_scheduler
from settings import ensure_auth_token, get_auth_token, get_discord_bot_token, logger
from socket_service import wrap_app_with_socketio


_AUTH_COOKIE_NAME = "auth_token"
_AUTH_BYPASS_PATHS = {
    "/api/auth/session",
    "/api/health",
    "/api/internal/discord/notify",  # localhost-only; handler enforces IP check
}


def _sanitize_single_line_secret(value: str) -> str:
    return re.sub(r"[\r\n]+", "", value).strip()


def create_app():
    ensure_auth_token()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    wrap_app_with_socketio(app)

    @app.middleware("http")
    async def _auth_middleware(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        if path in _AUTH_BYPASS_PATHS:
            return await call_next(request)

        expected = _sanitize_single_line_secret(get_auth_token())
        cookie_token = _sanitize_single_line_secret(request.cookies.get(_AUTH_COOKIE_NAME, ""))
        authorized_by_cookie = bool(expected and cookie_token and secrets.compare_digest(cookie_token, expected))
        if not authorized_by_cookie:
            return JSONResponse(status_code=401, content={"error": "unauth"})

        return await call_next(request)

    repo_root = Path(__file__).resolve().parents[2]
    bridge_service = MCPBridgeSocketService(
        config_path=repo_root / "config" / "mcp.json5",
        socket_path=repo_root / ".skillpilot/temp" / "engine.sock",
    )
    app.state.mcp_bridge_service = bridge_service

    @app.on_event("startup")
    async def _startup_mcp_bridge() -> None:
        import logging as _logging
        from main import _HeartbeatFilter
        access_logger = _logging.getLogger("uvicorn.access")
        if not any(isinstance(f, _HeartbeatFilter) for f in access_logger.filters):
            access_logger.addFilter(_HeartbeatFilter())
        bridge_service.start()
        logger.info("MCP bridge socket started at %s", bridge_service.socket_path)
        try:
            probe_results = bridge_service.probe_servers()
            for item in probe_results:
                server_id = item.get("server_id", "unknown")
                status = item.get("status")
                if status == "ok":
                    logger.info("MCP loaded: %s (%s tools)", server_id, item.get("tool_count", 0))
                elif status == "skipped":
                    logger.info("MCP skipped: %s (%s)", server_id, item.get("reason", ""))
                else:
                    logger.warning("MCP failed: %s (%s)", server_id, item.get("reason", "unknown error"))
        except Exception as exc:
            logger.warning("MCP probe failed: %s", exc)
        start_heartbeat_watcher()
        logger.info("Heartbeat watcher started")
        cleanup_stale_workflow_session()
        try:
            start_scheduler(load_schedules())
        except Exception as exc:
            logger.warning("Failed to start scheduler: %s", exc)
        discord_token = get_discord_bot_token()
        if discord_token:
            import asyncio
            from discord_bot import start_bot
            asyncio.create_task(start_bot(discord_token))
            logger.info("Discord bot starting")

    @app.on_event("shutdown")
    async def _shutdown_mcp_bridge() -> None:
        bridge_service.stop()
        logger.info("MCP bridge socket stopped")
        try:
            stop_scheduler()
            logger.info("Scheduler stopped")
        except Exception as exc:
            logger.warning("Failed to stop scheduler: %s", exc)
        try:
            from discord_bot import bot
            if not bot.is_closed():
                await bot.close()
                logger.info("Discord bot stopped")
        except Exception as exc:
            logger.warning("Failed to stop Discord bot: %s", exc)
        try:
            removed = _cleanup_webui_tmux_sessions()
            logger.info("Cleaned up %d webui tmux sessions on shutdown", removed)
        except Exception as exc:
            logger.warning("Failed to cleanup tmux sessions on shutdown: %s", exc)

    webui_www_dir = Path(__file__).resolve().parent.parent / "webui" / "www"
    if webui_www_dir.exists() and webui_www_dir.is_dir():
        logger.info("Serving static webui from %s", webui_www_dir)
        app.mount("/", StaticFiles(directory=str(webui_www_dir), html=True), name="webui-static")
    else:
        logger.warning("WebUI static folder not found. Build and export webui to www first.")

    return app
