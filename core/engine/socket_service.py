import json
from datetime import datetime
from typing import Any, Dict, Optional, Set

import socketio
from settings import LOCAL_CHROME_TOKEN, LOCAL_DEV_TOKEN, logger

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
SYSTEM_INFO = {"info": "Please wait for assignment", "zoom": ""}
ASSIGNMENT_TOKEN_BY_SID: Dict[str, str] = {}
CONTAINER_TOKEN_BY_SID: Dict[str, str] = {}
VSCODE_TOKEN_BY_SID: Dict[str, str] = {}
CHROME_TOKEN_BY_SID: Dict[str, str] = {}
ASSIGNMENT_SIDS_BY_TOKEN: Dict[str, Set[str]] = {}
CONTAINER_SIDS_BY_TOKEN: Dict[str, Set[str]] = {}
VSCODE_SIDS_BY_TOKEN: Dict[str, Set[str]] = {}
CHROME_SIDS_BY_TOKEN: Dict[str, Set[str]] = {}
CONTAINER_STATUS_BY_TOKEN: Dict[str, Dict[str, Any]] = {}


def _track_sid(
    sid: str,
    token: str,
    sid_to_token: Dict[str, str],
    token_to_sids: Dict[str, Set[str]],
) -> None:
    old_token = sid_to_token.get(sid)
    if old_token and old_token != token and old_token in token_to_sids:
        token_to_sids[old_token].discard(sid)
        if not token_to_sids[old_token]:
            token_to_sids.pop(old_token, None)
    sid_to_token[sid] = token
    token_to_sids.setdefault(token, set()).add(sid)


def _drop_tracked_sid(
    sid: str,
    sid_to_token: Dict[str, str],
    token_to_sids: Dict[str, Set[str]],
) -> None:
    token = sid_to_token.pop(sid, None)
    if not token:
        return
    sids = token_to_sids.get(token)
    if not sids:
        return
    sids.discard(sid)
    if not sids:
        token_to_sids.pop(token, None)


def _drop_sid(sid: str) -> None:
    _drop_tracked_sid(sid, ASSIGNMENT_TOKEN_BY_SID, ASSIGNMENT_SIDS_BY_TOKEN)
    _drop_tracked_sid(sid, CONTAINER_TOKEN_BY_SID, CONTAINER_SIDS_BY_TOKEN)
    _drop_tracked_sid(sid, VSCODE_TOKEN_BY_SID, VSCODE_SIDS_BY_TOKEN)
    _drop_tracked_sid(sid, CHROME_TOKEN_BY_SID, CHROME_SIDS_BY_TOKEN)


@sio.event
async def connect(sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, Any]]) -> None:
    _ = environ
    _ = auth
    await sio.emit("connected", {"type": "control", "payload": SYSTEM_INFO}, to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    _drop_sid(sid)


@sio.on("assignment_event")
async def on_assignment_event(sid: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    event_type = payload.get("type")
    if event_type == "sign-in":
        token = str(payload.get("token") or "").strip()
        if not token:
            await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": "no-assignment"}}, to=sid)
            return
        if token != LOCAL_DEV_TOKEN:
            await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": "invalid-token"}}, to=sid)
            return
        _track_sid(sid, LOCAL_DEV_TOKEN, ASSIGNMENT_TOKEN_BY_SID, ASSIGNMENT_SIDS_BY_TOKEN)
        await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": None}}, to=sid)
        return

    token = ASSIGNMENT_TOKEN_BY_SID.get(sid)
    if not token:
        await sio.emit("server_event", {"type": "sign-in-request", "payload": {"error": "no-member"}}, to=sid)
        return

    route_token = LOCAL_DEV_TOKEN

    if event_type == "get-container":
        target_token = route_token
        online_count = len(CONTAINER_SIDS_BY_TOKEN.get(target_token, set()))
        status = "online" if online_count > 0 else "offline"
        info = CONTAINER_STATUS_BY_TOKEN.get(target_token) or {}
        await sio.emit(
            "server_event",
            {
                "type": "container-status",
                "status": status,
                "devServer": "online" if online_count > 0 else "offline",
                "info": json.dumps(info) if info else "{}",
            },
            to=sid,
        )
        return

    containers = CONTAINER_SIDS_BY_TOKEN.get(route_token, set())
    if event_type == "shell" and payload.get("cmd") == ":get_online_container" and not containers:
        await sio.emit("server_event", {"type": "server-response", "payload": {"error": "wait-for-vscode"}}, to=sid)
        return
    if not containers:
        await sio.emit("server_event", {"type": "server-response", "payload": {"error": "no-container-online"}}, to=sid)
        return

    for container_sid in list(containers):
        await sio.emit("assignment_event", payload, to=container_sid)


@sio.on("chrome_event")
async def on_chrome_event(sid: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    event_type = payload.get("type")
    if event_type == "sign-in":
        token = str(payload.get("token") or "").strip()
        if not token:
            await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": "no-chrome"}}, to=sid)
            return
        if token != LOCAL_CHROME_TOKEN:
            await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": "invalid-token"}}, to=sid)
            return
        _track_sid(sid, LOCAL_CHROME_TOKEN, CHROME_TOKEN_BY_SID, CHROME_SIDS_BY_TOKEN)
        await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": None}}, to=sid)
        return

    token = CHROME_TOKEN_BY_SID.get(sid)
    if not token:
        await sio.emit("server_event", {"type": "sign-in-request", "payload": {"error": "no-chrome"}}, to=sid)
        return

    if event_type == "kill-pilot-task":
        task_payload = payload.get("payload")
        if not isinstance(task_payload, dict):
            task_payload = payload

        page_url = str(task_payload.get("pageUrl") or task_payload.get("page_url") or "").strip()
        selected_text = str(task_payload.get("selectedText") or task_payload.get("selected_text") or "").strip()
        task_description = str(
            task_payload.get("taskDescription") or task_payload.get("task_description") or ""
        ).strip()

        logger.info(
            "[kill-pilot-task] sid=%s page_url=%s selected_text=%s task_description=%s",
            sid,
            page_url,
            selected_text,
            task_description,
        )
        await sio.emit("server_event", {"type": "kill-pilot-task-received", "payload": {"error": None}}, to=sid)
        return


@sio.on("container_event")
async def on_container_event(sid: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    event_type = payload.get("type")
    if event_type == "sign-in":
        token = str(payload.get("token") or "").strip()
        if not token:
            await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": "no-container"}}, to=sid)
            return

        _track_sid(sid, token, CONTAINER_TOKEN_BY_SID, CONTAINER_SIDS_BY_TOKEN)
        if payload.get("src") == "vscode":
            _track_sid(sid, token, VSCODE_TOKEN_BY_SID, VSCODE_SIDS_BY_TOKEN)
        else:
            _drop_tracked_sid(sid, VSCODE_TOKEN_BY_SID, VSCODE_SIDS_BY_TOKEN)
        CONTAINER_STATUS_BY_TOKEN[token] = {
            "container_version": payload.get("container_version"),
            "src": payload.get("src"),
            "version": payload.get("version"),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await sio.emit("server_event", {"type": "sign-in-response", "payload": {"error": None}}, to=sid)

        assignment_sids = ASSIGNMENT_SIDS_BY_TOKEN.get(token, set())
        if payload.get("src") == "vscode":
            response = {
                "type": "shell",
                "cmd": ":get_online_container",
                "dir": "/tmp",
                "regx": "v1",
                "response": json.dumps({"container_version": payload.get("container_version")}),
                "error": "Please wait until it is ready to use.",
            }
            for assignment_sid in list(assignment_sids):
                await sio.emit("container_event", response, to=assignment_sid)
        return

    token = CONTAINER_TOKEN_BY_SID.get(sid)
    if not token:
        await sio.emit("server_event", {"type": "sign-in-request", "payload": {"error": "no-member"}}, to=sid)
        return

    assignments = ASSIGNMENT_SIDS_BY_TOKEN.get(token, set())
    if not assignments:
        await sio.emit("server_event", {"type": "server-response", "payload": {"error": "no-assignment-online"}}, to=sid)
        return

    for assignment_sid in list(assignments):
        await sio.emit("container_event", payload, to=assignment_sid)


async def emit_to_vscode_clients(local_dev_token: str, payload: Dict[str, Any]) -> int:
    token = str(local_dev_token or "").strip()
    if not token:
        return 0
    recipients = list(VSCODE_SIDS_BY_TOKEN.get(token, set()))
    if not recipients:
        return 0
    for sid in recipients:
        await sio.emit("assignment_event", payload, to=sid)
    return len(recipients)


def wrap_app_with_socketio(app: Any) -> Any:
    socketio_app = socketio.ASGIApp(sio, socketio_path="")
    app.mount("/socket.io", socketio_app)
    return app
