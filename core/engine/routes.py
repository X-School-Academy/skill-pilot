import asyncio
import base64
import fcntl
import ipaddress
import json
import os
import pty
import re
import secrets
import shlex
import shutil
import socket
import signal
import struct
import subprocess
import sys
import termios
import time
import urllib.parse
import urllib.request
from uuid import uuid4
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from apscheduler.triggers.cron import CronTrigger

from code_executor import execute_code_impl
from course_utils import build_tree, find_latest_course, read_course_meta, safe_course_path, write_course_meta
from dev_swarm.router import router as dev_swarm_router
import json5
from workflow_editor_utils import (
    build_workflow_tree,
    find_latest_workflow,
    is_valid_workflow_filename,
    normalize_workflow_filename,
    safe_workflow_path,
    validate_workflow_doc,
)

from llm_service import (
    build_chat_system_message,
    build_code_system_message,
    build_llm_command,
    build_terminal_command,
    build_translate_system_message,
    get_default_llm_provider_id,
    get_provider,
    llm_stream,
    load_llm_providers,
    load_provider_config,
    stop_client,
)
from socket_service import emit_to_vscode_clients
from settings import (
    COURSES_DIR,
    PROJECT_DIR,
    WORKFLOWS_DIR,
    LOCAL_DEV_TOKEN,
    TERMINAL_AUTO_IMAGE_URL_PREVIEW,
    get_auth_token,
    get_discord_bot_token,
    get_only_allow_https,
    get_live_avatar_server_url,
    get_turn_server_urls,
    get_turn_server_username,
    get_turn_server_password,
    logger,
)
from safe_dotenv import safe_env
from session_agent_store import set_session_agent_meta
from workflow import CoursePlannerWorkflow, VideoCreatorWorkflow

router = APIRouter()
router.include_router(dev_swarm_router)
COURSE_PLANNER = CoursePlannerWorkflow()
VIDEO_CREATOR = VideoCreatorWorkflow()
_IMAGE_URL_PATTERN = re.compile(
    rb"https?://[^\s<>'\"`]+?\.(?:png|jpe?g|gif)(?:\?[^\s<>'\"`]*)?",
    re.IGNORECASE,
)
_IMAGE_FETCH_TIMEOUT_SECONDS = 3.0
_IMAGE_FETCH_MAX_BYTES = 5 * 1024 * 1024
TMUX_SESSION_PREFIX = "webui-live-"
NATIVE_TMUX_SESSION_PREFIX = "native-terminal-"
TMUX_SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_last_heartbeat_time: float = time.time()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_CONFIG_PATH = _REPO_ROOT / "config" / "mcp.json5"
_MCP_SERVER_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_MCP_SKILLS_DIR = _REPO_ROOT / "core" / "skills" / "mcp"
_SYSTEM_SKILLS_DIR = _REPO_ROOT / "core" / "skills" / "system"
_DISABLED_SKILLS_PATH = _REPO_ROOT / "config" / "disabled_skills.json"
_SKILL_CATEGORIES: List[tuple[str, str, Path]] = [
    ("system", "System", _REPO_ROOT / "core" / "skills" / "system"),
    ("dev-swarm", "Dev Swarm", _REPO_ROOT / "dev-swarm" / "skills"),
    ("mcp", "MCP", _REPO_ROOT / "core" / "skills" / "mcp"),
    ("third-party", "Third Party", _REPO_ROOT / "core" / "skills" / "third-party"),
    ("user", "User", _REPO_ROOT / "core" / "skills" / "user"),
]
_HEARTBEAT_TIMEOUT_SECONDS = 10.0
_heartbeat_watcher_started = False
_last_native_cleanup_time: float = 0.0
_NATIVE_STALE_CLEANUP_INTERVAL_SECONDS = 60.0
_SETTINGS_PATH = _REPO_ROOT / "config" / "settings.json5"
_AI_PROVIDERS_PATH = _REPO_ROOT / "config" / "ai_providers.json5"
_CONFIG_ENV_PATH = _REPO_ROOT / "config" / ".env"
_AUTH_COOKIE_NAME = "auth_token"
_AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "security": {
        "schedules": {"sandbox": True, "auto": True, "network": True},
        "newSession": {"sandbox": False, "auto": False, "network": True},
        "remoteBot": {"sandbox": True, "auto": True, "network": False},
        "devSwarm": {"sandbox": True, "auto": True, "network": True},
        "skillAgent": {},
    },
}


def _read_settings() -> Dict[str, Any]:
    if not _SETTINGS_PATH.is_file():
        return dict(_DEFAULT_SETTINGS)
    try:
        data = json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(_DEFAULT_SETTINGS)
            merged.update(data)
            merged_security = dict(_DEFAULT_SETTINGS.get("security", {}))
            data_security = data.get("security")
            if isinstance(data_security, dict):
                for section, defaults in _DEFAULT_SETTINGS.get("security", {}).items():
                    candidate = data_security.get(section)
                    if isinstance(defaults, dict):
                        merged_section = dict(defaults)
                        if isinstance(candidate, dict):
                            merged_section.update(candidate)
                        merged_security[section] = merged_section
                    elif candidate is not None:
                        merged_security[section] = candidate
            merged["security"] = merged_security
            return merged
    except Exception as exc:
        logger.warning("Failed to read settings: %s", exc)
    return dict(_DEFAULT_SETTINGS)


def _write_settings(data: Dict[str, Any]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _record_tmux_agent_meta(
    session_name: str,
    provider: Dict[str, Any],
    sandbox: Any,
    auto: Any,
    network: Any,
) -> None:
    set_session_agent_meta(session_name, {
        "provider_id": str(provider.get("id") or "").strip(),
        "provider_bin": str(provider.get("bin") or "").strip(),
        "sandbox": _bool_with_default(sandbox, False),
        "auto": _bool_with_default(auto, False),
        "network": _bool_with_default(network, True),
        "updated_at": int(time.time()),
    })


def _bool_with_default(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return bool(value)


def _sanitize_single_line_secret(value: str) -> str:
    return re.sub(r"[\r\n]+", "", value).strip()


def _is_authorized_request(request: Request) -> bool:
    cookie_token = _sanitize_single_line_secret(request.cookies.get(_AUTH_COOKIE_NAME, ""))
    expected = _sanitize_single_line_secret(get_auth_token())
    if not cookie_token or not expected:
        return False
    return secrets.compare_digest(cookie_token, expected)


def _auth_required_response() -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": "auth required"})


def _is_public_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    try:
        host = urllib.parse.urlparse(url).hostname
    except ValueError:
        return False
    if not host:
        return False
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for item in addresses:
        ip_text = item[4][0]
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def _build_iip_sequence_for_url(url: str) -> bytes | None:
    if not _is_public_url(url):
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "JuniorIT-Terminal/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_IMAGE_FETCH_TIMEOUT_SECONDS) as resp:
            if resp.status < 200 or resp.status >= 300:
                return None
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if content_type and not content_type.startswith("image/"):
                return None
            data = resp.read(_IMAGE_FETCH_MAX_BYTES + 1)
            if not data or len(data) > _IMAGE_FETCH_MAX_BYTES:
                return None
    except OSError:
        return None
    encoded = base64.b64encode(data)
    image = (
        b"\x1b]1337;File=inline=1;width=50%;height=50%;preserveAspectRatio=1;size="
        + str(len(data)).encode()
        + b":"
        + encoded
        + b"\x07"
    )
    url_bytes = url.encode("utf-8", errors="replace")
    link = b"\x1b]8;;" + url_bytes + b"\x07Open image in new tab\x1b]8;;\x07"
    return image + b"\r\n" + url_bytes + b"\r\n" + link + b"\r\n"


async def _replace_image_urls_with_iip(payload: bytes, cache: Dict[bytes, bytes]) -> bytes:
    matches = list(_IMAGE_URL_PATTERN.finditer(payload))
    if not matches:
        return payload

    out: list[bytes] = []
    start = 0
    for match in matches:
        out.append(payload[start : match.start()])
        url_bytes = match.group(0)
        replacement = cache.get(url_bytes)
        if replacement is None:
            try:
                url_text = url_bytes.decode("ascii")
            except UnicodeDecodeError:
                replacement = url_bytes
            else:
                iip_sequence = await asyncio.to_thread(_build_iip_sequence_for_url, url_text)
                replacement = iip_sequence if iip_sequence else url_bytes
            cache[url_bytes] = replacement
        out.append(replacement)
        start = match.end()
    out.append(payload[start:])
    return b"".join(out)


def _coerce_command(command: str) -> str:
    value = (command or "").strip()
    return value or "top"


def _validate_tmux_session_name(session_name: str) -> str:
    value = (session_name or "").strip()
    if not value:
        raise ValueError("tmux session name is required")
    if not value.startswith(TMUX_SESSION_PREFIX):
        raise ValueError(f"tmux session must start with '{TMUX_SESSION_PREFIX}'")
    if not TMUX_SESSION_NAME_RE.fullmatch(value):
        raise ValueError("invalid tmux session name format")
    return value


def _validate_tmux_session_name_any(session_name: str) -> str:
    value = (session_name or "").strip()
    if not value:
        raise ValueError("tmux session name is required")
    if not TMUX_SESSION_NAME_RE.fullmatch(value):
        raise ValueError("invalid tmux session name format")
    return value


def _ensure_tmux_available() -> None:
    if shutil.which("tmux") is None:
        raise RuntimeError("tmux is not installed or not available in PATH")


def _run_tmux_command(args: List[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    _ensure_tmux_available()
    proc = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
        shell=False,
        env=safe_env(),
    )
    if check and proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"tmux command failed: {' '.join(args)}")
    return proc


def _list_webui_tmux_sessions() -> List[Dict[str, Any]]:
    proc = _run_tmux_command(
        ["ls", "-F", "#{session_name}\t#{session_attached}\t#{session_created}\t#{session_windows}"],
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip().lower()
        if "failed to connect to server" in message or "no server running" in message:
            return []
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to list tmux sessions")

    sessions: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split("\t")
        name = parts[0].strip() if parts else ""
        if not name.startswith(TMUX_SESSION_PREFIX):
            continue
        attached_raw = parts[1].strip() if len(parts) > 1 else "0"
        created_raw = parts[2].strip() if len(parts) > 2 else "0"
        windows_raw = parts[3].strip() if len(parts) > 3 else "0"
        try:
            created_at = int(created_raw)
        except ValueError:
            created_at = 0
        try:
            windows = int(windows_raw)
        except ValueError:
            windows = 0
        sessions.append(
            {
                "name": name,
                "attached": attached_raw == "1",
                "created_at": created_at,
                "windows": windows,
            }
        )
    sessions.sort(key=lambda item: item["name"])
    return sessions


def _list_native_tmux_sessions() -> List[Dict[str, Any]]:
    proc = _run_tmux_command(
        [
            "ls",
            "-F",
            "#{session_name}\t#{session_attached}\t#{session_created}\t#{session_windows}\t#{session_activity}",
        ],
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip().lower()
        if "failed to connect to server" in message or "no server running" in message:
            return []
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to list tmux sessions")

    sessions: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split("\t")
        name = parts[0].strip() if parts else ""
        if not name.startswith(NATIVE_TMUX_SESSION_PREFIX):
            continue
        attached_raw = parts[1].strip() if len(parts) > 1 else "0"
        created_raw = parts[2].strip() if len(parts) > 2 else "0"
        windows_raw = parts[3].strip() if len(parts) > 3 else "0"
        activity_raw = parts[4].strip() if len(parts) > 4 else "0"
        try:
            created_at = int(created_raw)
        except ValueError:
            created_at = 0
        try:
            windows = int(windows_raw)
        except ValueError:
            windows = 0
        try:
            activity_at = int(activity_raw)
        except ValueError:
            activity_at = 0
        sessions.append(
            {
                "name": name,
                "attached": attached_raw == "1",
                "created_at": created_at,
                "windows": windows,
                "activity_at": activity_at,
            }
        )
    sessions.sort(key=lambda item: item["name"])
    return sessions


def _list_external_tmux_sessions() -> List[Dict[str, Any]]:
    proc = _run_tmux_command(
        ["ls", "-F", "#{session_name}\t#{session_attached}\t#{session_created}\t#{session_windows}"],
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip().lower()
        if "failed to connect to server" in message or "no server running" in message:
            return []
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to list tmux sessions")

    sessions: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split("\t")
        name = parts[0].strip() if parts else ""
        if name.startswith(TMUX_SESSION_PREFIX):
            continue
        if not name:
            continue
        attached_raw = parts[1].strip() if len(parts) > 1 else "0"
        created_raw = parts[2].strip() if len(parts) > 2 else "0"
        windows_raw = parts[3].strip() if len(parts) > 3 else "0"
        try:
            created_at = int(created_raw)
        except ValueError:
            created_at = 0
        try:
            windows = int(windows_raw)
        except ValueError:
            windows = 0
        sessions.append(
            {
                "name": name,
                "attached": attached_raw == "1",
                "created_at": created_at,
                "windows": windows,
            }
        )
    sessions.sort(key=lambda item: item["name"])
    return sessions


def _tmux_session_exists(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name_any(session_name)
    proc = _run_tmux_command(["has-session", "-t", safe_name], check=False)
    return proc.returncode == 0


def _build_tmux_attach_command(session_name: str, readonly: bool = False) -> str:
    safe_name = _validate_tmux_session_name(session_name)
    readonly_flag = " -r" if readonly else ""
    return f"tmux attach -t {shlex.quote(safe_name)}{readonly_flag}"


def _build_tmux_attach_command_any(session_name: str, readonly: bool = False) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    readonly_flag = " -r" if readonly else ""
    return f"tmux attach -t {shlex.quote(safe_name)}{readonly_flag}"


def _create_webui_tmux_session(command: str) -> str:
    session_name = f"{TMUX_SESSION_PREFIX}{int(time.time())}-{secrets.token_hex(2)}"
    safe_command = _coerce_command(command)
    _run_tmux_command(
        ["new-session", "-d", "-s", session_name, "/bin/bash"],
        check=True,
    )
    _run_tmux_command(["send-keys", "-t", session_name, safe_command, "Enter"], check=True)
    return session_name


def _create_native_tmux_session(command: str) -> str:
    session_name = f"{NATIVE_TMUX_SESSION_PREFIX}{int(time.time())}-{secrets.token_hex(2)}"
    safe_command = _coerce_command(command)
    _run_tmux_command(
        ["new-session", "-d", "-s", session_name, "/bin/bash"],
        check=True,
    )
    _run_tmux_command(["send-keys", "-t", session_name, safe_command, "Enter"], check=True)
    return session_name


def _kill_tmux_session(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name(session_name)
    proc = _run_tmux_command(["kill-session", "-t", safe_name], check=False)
    if proc.returncode == 0:
        return True
    message = (proc.stderr or proc.stdout or "").lower()
    if "can't find session" in message:
        return False
    raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to kill tmux session")


def _cleanup_webui_tmux_sessions() -> int:
    removed_count = 0
    for session in _list_webui_tmux_sessions():
        try:
            if _kill_tmux_session(session["name"]):
                removed_count += 1
        except RuntimeError as exc:
            logger.warning("failed to remove tmux session %s: %s", session["name"], exc)
    return removed_count


def _cleanup_stale_native_tmux_sessions() -> int:
    removed_count = 0
    for session in _list_native_tmux_sessions():
        if session.get("attached"):
            continue
        name = str(session.get("name") or "")
        if not name:
            continue
        proc = _run_tmux_command(["kill-session", "-t", name], check=False)
        if proc.returncode == 0:
            removed_count += 1
            continue
        message = (proc.stderr or proc.stdout or "").lower()
        if "can't find session" in message:
            continue
        logger.warning("failed to remove stale native tmux session %s: %s", name, (proc.stderr or proc.stdout or "").strip())
    return removed_count


def _open_native_terminal_for_tmux(session_name: str) -> Dict[str, Any]:
    safe_session = _validate_tmux_session_name_any(session_name)
    if sys.platform == "darwin":
        script_cmd = f"tmux attach -t {safe_session}"
        escaped_script_cmd = script_cmd.replace("\\", "\\\\").replace('"', '\\"')
        apple_script = f'tell application "Terminal" to do script "{escaped_script_cmd}"'
        try:
            subprocess.Popen(
                ["osascript", "-e", apple_script, "-e", 'tell application "Terminal" to activate'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=safe_env(),
            )
            return {"opened": True, "method": "osascript-terminal", "session": safe_session}
        except Exception as exc:
            return {"opened": False, "method": "osascript-terminal", "error": str(exc), "session": safe_session}

    candidates: List[List[str]] = []
    if shutil.which("x-terminal-emulator"):
        candidates.append(["x-terminal-emulator", "-e", "tmux", "attach", "-t", safe_session])
    if shutil.which("gnome-terminal"):
        candidates.append(["gnome-terminal", "--", "tmux", "attach", "-t", safe_session])
    if shutil.which("konsole"):
        candidates.append(["konsole", "-e", "tmux", "attach", "-t", safe_session])
    if shutil.which("xfce4-terminal"):
        candidates.append(["xfce4-terminal", "-x", "tmux", "attach", "-t", safe_session])
    if shutil.which("xterm"):
        candidates.append(["xterm", "-e", "tmux", "attach", "-t", safe_session])

    if not candidates:
        return {
            "opened": False,
            "error": "No supported native terminal launcher found (x-terminal-emulator/gnome-terminal/konsole/xfce4-terminal/xterm).",
            "session": safe_session,
        }

    for cmd in candidates:
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=safe_env(),
                start_new_session=True,
            )
            return {"opened": True, "method": cmd[0], "session": safe_session}
        except Exception:
            continue

    return {"opened": False, "error": "Failed to launch native terminal", "session": safe_session}


def _set_pty_size(fd: int, cols: int, rows: int) -> None:
    cols = max(20, min(int(cols or 80), 500))
    rows = max(5, min(int(rows or 24), 200))
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _notify_sigwinch(master_fd: int, proc: subprocess.Popen[Any] | None) -> None:
    # Signal the current foreground job first; ncurses apps (e.g. htop) react immediately.
    try:
        fg_pgrp = os.tcgetpgrp(master_fd)
        if fg_pgrp > 0:
            os.killpg(fg_pgrp, signal.SIGWINCH)
            return
    except (OSError, ProcessLookupError):
        pass

    # Fallback to the spawned process group.
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGWINCH)
        except (OSError, ProcessLookupError):
            try:
                os.kill(proc.pid, signal.SIGWINCH)
            except (OSError, ProcessLookupError):
                pass


async def _terminate_process(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            proc.terminate()
        except (ProcessLookupError, PermissionError, OSError):
            return
    except OSError:
        try:
            proc.terminate()
        except (ProcessLookupError, PermissionError, OSError):
            return
    try:
        await asyncio.to_thread(proc.wait, 1.5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except PermissionError:
            try:
                proc.kill()
            except (ProcessLookupError, PermissionError, OSError):
                return
        except OSError:
            try:
                proc.kill()
            except (ProcessLookupError, PermissionError, OSError):
                return


@router.get("/api/health")
def health():
    return {"status": "ok", "timestamp": time.time()}


@router.get("/api/local-dev-token")
def local_dev_token():
    return {"token": LOCAL_DEV_TOKEN}


@router.get("/api/terminal")
def terminal_api(command: str = Query("top"), session: str | None = Query(None), readonly: int = Query(0)):
    is_readonly = int(readonly or 0) == 1
    if session:
        try:
            if is_readonly:
                safe_session = _validate_tmux_session_name_any(session)
            else:
                safe_session = _validate_tmux_session_name(session)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        readonly_param = "&readonly=1" if is_readonly else ""
        if is_readonly:
            attach_command = _build_tmux_attach_command_any(safe_session, readonly=True)
        else:
            attach_command = _build_tmux_attach_command(safe_session)
        return {
            "session": safe_session,
            "command": attach_command,
            "websocket_path": f"/api/terminal/ws?session={quote(safe_session)}{readonly_param}",
        }

    safe_command = _coerce_command(command)
    return {
        "command": safe_command,
        "websocket_path": f"/api/terminal/ws?command={quote(safe_command)}",
    }


@router.get("/api/terminal/tmux/sessions")
def terminal_tmux_sessions():
    try:
        sessions = _list_webui_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "sessions": []})
    return {"sessions": sessions}


@router.get("/api/terminal/tmux/external-sessions")
def terminal_tmux_external_sessions():
    try:
        sessions = _list_external_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "sessions": []})
    return {"sessions": sessions}


@router.post("/api/terminal/tmux/create")
def terminal_tmux_create(payload: Dict[str, Any]):
    prompt = (str(payload.get("prompt") or "")).strip()
    provider_id = (str(payload.get("provider_id") or "")).strip() or None
    native_terminal = _bool_with_default(payload.get("native_terminal"), False)
    provider: Dict[str, Any] | None = None
    sandbox = payload.get("sandbox")
    auto = payload.get("auto")
    network = payload.get("network")

    if prompt:
        provider = get_provider(provider_id)
        cmd_list = build_terminal_command(
            provider,
            prompt,
            auto_allow=auto,
            network_allow=network,
            sandbox_mode=sandbox,
        )
        if provider.get("id") == "opencode" and auto:
            opencode_config = str(_REPO_ROOT / "config" / "opencode-yolo.json")
            command = f"OPENCODE_CONFIG={shlex.quote(opencode_config)} {shlex.join(cmd_list)}"
        else:
            command = shlex.join(cmd_list)
        logger.info("[tmux-create] provider=%s command=%s", provider.get("id"), command)
    else:
        command = _coerce_command(str(payload.get("command") or ""))
        logger.info("[tmux-create] raw command=%s", command)

    try:
        if native_terminal:
            session_name = _create_native_tmux_session(command)
            native_status = _open_native_terminal_for_tmux(session_name)
            attach_command = _build_tmux_attach_command_any(session_name)
        else:
            session_name = _create_webui_tmux_session(command)
            native_status = {"requested": False, "opened": False}
            attach_command = _build_tmux_attach_command(session_name)
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    if native_terminal and "requested" not in native_status:
        native_status["requested"] = True
    if provider is not None:
        try:
            _record_tmux_agent_meta(session_name, provider, sandbox=sandbox, auto=auto, network=network)
        except Exception as exc:
            logger.warning("failed to record tmux agent meta for %s: %s", session_name, exc)

    return {
        "session": {
            "name": session_name,
            "command": command,
            "attach_command": attach_command,
        },
        "native_terminal": native_status,
    }


@router.post("/api/terminal/tmux/kill")
def terminal_tmux_kill(payload: Dict[str, Any]):
    try:
        session_name = _validate_tmux_session_name(str(payload.get("session") or ""))
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    try:
        removed = _kill_tmux_session(session_name)
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "removed": removed, "session": session_name}


@router.post("/api/terminal/tmux/cleanup")
def terminal_tmux_cleanup():
    try:
        removed_count = _cleanup_webui_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "removed_count": 0})
    return {"status": "ok", "removed_count": removed_count}


@router.post("/api/terminal/tmux/cleanup-native-stale")
def terminal_tmux_cleanup_native_stale():
    try:
        removed_count = _cleanup_stale_native_tmux_sessions()
    except RuntimeError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "removed_count": 0})
    return {"status": "ok", "removed_count": removed_count}


@router.post("/api/heartbeat")
def heartbeat():
    global _last_heartbeat_time
    _last_heartbeat_time = time.time()
    return {"status": "ok", "timestamp": _last_heartbeat_time}


async def _heartbeat_watcher() -> None:
    global _last_heartbeat_time, _last_native_cleanup_time
    while True:
        await asyncio.sleep(5)
        elapsed = time.time() - _last_heartbeat_time
        if elapsed > _HEARTBEAT_TIMEOUT_SECONDS:
            sessions = _list_webui_tmux_sessions()
            if sessions:
                logger.info("[heartbeat] no heartbeat for %.1fs, cleaning up %d webui tmux sessions", elapsed, len(sessions))
                _cleanup_webui_tmux_sessions()
                _last_heartbeat_time = time.time()
        now = time.time()
        if now - _last_native_cleanup_time >= _NATIVE_STALE_CLEANUP_INTERVAL_SECONDS:
            try:
                removed = _cleanup_stale_native_tmux_sessions()
                if removed > 0:
                    logger.info("[heartbeat] cleaned up %d stale native tmux session(s)", removed)
            except Exception as exc:
                logger.warning("failed native stale tmux cleanup: %s", exc)
            _last_native_cleanup_time = now


def start_heartbeat_watcher() -> None:
    global _heartbeat_watcher_started
    if not _heartbeat_watcher_started:
        _heartbeat_watcher_started = True
        asyncio.create_task(_heartbeat_watcher())


@router.get("/api/config/settings")
def config_settings_get():
    try:
        return _read_settings()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/config/env-safeguard-status")
def config_env_safeguard_status():
    try:
        exists = _CONFIG_ENV_PATH.is_file()
        if not exists:
            return {
                "enabled": False,
                "exists": False,
                "reason": "config/.env not found",
                "repo_root": str(_REPO_ROOT),
            }

        stat_result = _CONFIG_ENV_PATH.stat()
        mode = stat_result.st_mode & 0o777
        owner_is_root = stat_result.st_uid == 0
        readable = os.access(_CONFIG_ENV_PATH, os.R_OK)
        enabled = owner_is_root and mode == 0o600 and not readable
        if enabled:
            reason = "Safe guard is enabled."
        else:
            reason = "Safe guard is not enabled."

        return {
            "enabled": enabled,
            "exists": True,
            "reason": reason,
            "owner_uid": stat_result.st_uid,
            "mode": f"{mode:o}",
            "readable_by_process": readable,
            "repo_root": str(_REPO_ROOT),
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/config/settings")
async def config_settings_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    try:
        _write_settings(body)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok"}


_DEFAULT_LLM_RE = re.compile(
    r"""("default"\s*:\s*\{[^}]*?"llm"\s*:\s*)"([^"]*)" """.strip(),
    re.DOTALL,
)
_DEFAULT_LLM_RE_JSON5 = re.compile(
    r"""(default\s*:\s*\{[^}]*?llm\s*:\s*)'([^']*)' """.strip(),
    re.DOTALL,
)


@router.post("/api/config/default-provider")
async def config_default_provider(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    provider_id = (str(body.get("provider") or "")).strip()
    if not provider_id:
        return JSONResponse(status_code=400, content={"error": "provider is required"})
    try:
        text = _AI_PROVIDERS_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": f"Failed to read ai_providers: {exc}"})
    # Try double-quoted JSON keys first, then unquoted JSON5 keys
    new_text, count = _DEFAULT_LLM_RE.subn(rf'\g<1>"{provider_id}"', text, count=1)
    if count == 0:
        new_text, count = _DEFAULT_LLM_RE_JSON5.subn(rf"\g<1>'{provider_id}'", text, count=1)
    if count == 0:
        return JSONResponse(status_code=500, content={"error": "Could not find default.llm in ai_providers config"})
    try:
        _AI_PROVIDERS_PATH.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "provider": provider_id}


_PROFILE_PATH = _REPO_ROOT / "config" / "profile.json5"


def _get_local_timezone() -> str:
    try:
        import time as _time
        tz_name = _time.tzname[0] if _time.tzname else ""
        # Prefer IANA name from /etc/localtime or TZ env
        tz_env = os.environ.get("TZ", "")
        if tz_env:
            return tz_env
        localtime = Path("/etc/localtime")
        if localtime.is_symlink():
            target = str(localtime.resolve())
            if "/zoneinfo/" in target:
                return target.split("/zoneinfo/", 1)[1]
        return tz_name or "UTC"
    except Exception:
        return "UTC"


@router.get("/api/config/profile")
def config_profile_get():
    data: Dict[str, Any] = {}
    if _PROFILE_PATH.is_file():
        try:
            loaded = json5.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception as exc:
            logger.warning("Failed to read profile: %s", exc)
    if not data.get("timezone"):
        data["timezone"] = _get_local_timezone()
    return data


@router.post("/api/config/profile")
async def config_profile_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Profile must be a JSON object"})
    tz_value = (str(body.get("timezone") or "")).strip()
    if tz_value:
        import pytz
        try:
            pytz.timezone(tz_value)
        except pytz.exceptions.UnknownTimeZoneError:
            return JSONResponse(status_code=400, content={"error": f"Invalid timezone: {tz_value}"})
    _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _PROFILE_PATH.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok"}


@router.get("/api/config/timezones")
def config_timezones():
    import pytz
    return {"timezones": pytz.common_timezones}


def _read_mcp_config() -> Dict[str, Any]:
    if not _MCP_CONFIG_PATH.is_file():
        return {"mcpServers": {}}
    return json5.loads(_MCP_CONFIG_PATH.read_text(encoding="utf-8"))


def _write_mcp_config(data: Dict[str, Any]) -> None:
    _MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MCP_CONFIG_PATH.write_text(json5.dumps(data, indent=2) + "\n", encoding="utf-8")


def _infer_mcp_server_type(config: Dict[str, Any]) -> str:
    raw_type = config.get("type", "")
    if raw_type == "http":
        return "streamable-http"
    if raw_type == "sse":
        return "sse"
    return "stdio"


def _parse_bool_value(value: Any) -> bool:
    """Parse a potentially string-typed bool field from env expansion."""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return bool(value)


@router.get("/api/config/mcp-servers")
def config_mcp_servers_list():
    try:
        data = _read_mcp_config()
    except (ValueError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "servers": []})
    from mcp_servers.mcp_to_skills.sync import expand_env_placeholders
    expansion_env = dict(os.environ)
    servers_dict = data.get("mcpServers", {})
    servers = []
    for name, cfg in servers_dict.items():
        missing: set = set()
        expanded = expand_env_placeholders(cfg, expansion_env, missing)
        entry: Dict[str, Any] = {"name": name, "type": _infer_mcp_server_type(expanded)}
        if expanded.get("system"):
            entry["system"] = True
        enabled_raw = expanded.get("enabled")
        disabled_raw = expanded.get("disabled", False)
        if enabled_raw is not None:
            is_disabled = not _parse_bool_value(enabled_raw)
        else:
            is_disabled = _parse_bool_value(disabled_raw)
        if is_disabled:
            entry["disabled"] = True
        for field in ("command", "args", "env", "url", "headers"):
            if field in expanded:
                entry[field] = expanded[field]
        servers.append(entry)
    return {"servers": servers}


@router.post("/api/config/mcp-servers")
async def config_mcp_servers_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    name = (str(body.get("name") or "")).strip()
    if not name or not _MCP_SERVER_NAME_RE.fullmatch(name):
        return JSONResponse(status_code=400, content={"error": "Invalid server name. Use only letters, digits, hyphens, and underscores."})

    server_type = str(body.get("type") or "stdio").strip()
    if server_type not in ("stdio", "streamable-http", "sse"):
        return JSONResponse(status_code=400, content={"error": f"Invalid type: {server_type}"})

    try:
        data = _read_mcp_config()
    except (json.JSONDecodeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    servers = data.get("mcpServers", {})
    existing = servers.get(name)
    if existing and existing.get("system"):
        return JSONResponse(status_code=403, content={"error": f"Cannot modify system server: {name}"})

    entry: Dict[str, Any] = {}
    if server_type == "stdio":
        command = (str(body.get("command") or "")).strip()
        if not command:
            return JSONResponse(status_code=400, content={"error": "command is required for stdio type"})
        entry["command"] = command
        args = body.get("args")
        if isinstance(args, list) and args:
            entry["args"] = [str(a) for a in args]
        env = body.get("env")
        if isinstance(env, dict) and env:
            entry["env"] = {str(k): str(v) for k, v in env.items()}
    else:
        url = (str(body.get("url") or "")).strip()
        if not url:
            return JSONResponse(status_code=400, content={"error": "url is required for http/sse type"})
        entry["type"] = "http" if server_type == "streamable-http" else "sse"
        entry["url"] = url
        headers = body.get("headers")
        if isinstance(headers, dict) and headers:
            entry["headers"] = {str(k): str(v) for k, v in headers.items()}

    disabled = body.get("disabled")
    if disabled is True or disabled is False:
        entry["disabled"] = disabled

    servers[name] = entry
    data["mcpServers"] = servers
    try:
        _write_mcp_config(data)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    # Auto-install requirements.txt if enabling a stdio server that has one
    enabling = disabled is False or (disabled is None and not entry.get("disabled", False))
    if enabling and server_type == "stdio":
        req_path = _REPO_ROOT / "core" / "engine" / "mcp_servers" / name / "requirements.txt"
        if req_path.exists():
            engine_dir = str(_REPO_ROOT / "core" / "engine")
            req_rel = str(req_path.relative_to(_REPO_ROOT / "core" / "engine"))
            try:
                subprocess.run(
                    ["uv", "add", "-r", req_rel],
                    cwd=engine_dir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except Exception as exc:
                logger.warning("Failed to install requirements for %s: %s", name, exc)

    return {"status": "ok", "name": name}


@router.delete("/api/config/mcp-servers/{name}")
def config_mcp_servers_delete(name: str):
    name = name.strip()
    if not name or not _MCP_SERVER_NAME_RE.fullmatch(name):
        return JSONResponse(status_code=400, content={"error": "Invalid server name"})

    try:
        data = _read_mcp_config()
    except (json.JSONDecodeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    servers = data.get("mcpServers", {})
    existing = servers.get(name)
    if not existing:
        return JSONResponse(status_code=404, content={"error": f"Server not found: {name}"})
    if existing.get("system"):
        return JSONResponse(status_code=403, content={"error": f"Cannot delete system server: {name}"})

    del servers[name]
    data["mcpServers"] = servers
    try:
        _write_mcp_config(data)
    except OSError as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})
    return {"status": "ok", "name": name}


def _parse_skill_frontmatter(skill_md_path: Path) -> Dict[str, str]:
    text = skill_md_path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    result: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _read_disabled_skills() -> List[str]:
    if not _DISABLED_SKILLS_PATH.is_file():
        return []
    try:
        data = json5.loads(_DISABLED_SKILLS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(s) for s in data]
    except (ValueError, OSError):
        pass
    return []


@router.get("/api/config/skills")
def config_skills_list():
    disabled_set = set(_read_disabled_skills())
    categories = []
    for cat_id, cat_label, cat_dir in _SKILL_CATEGORIES:
        skills = []
        if cat_dir.is_dir():
            for child in sorted(cat_dir.iterdir()):
                skill_md = child / "SKILL.md"
                if child.is_dir() and skill_md.exists():
                    meta = _parse_skill_frontmatter(skill_md)
                    skills.append({
                        "name": meta.get("name", child.name),
                        "description": meta.get("description", ""),
                        "disabled": child.name in disabled_set,
                    })
        categories.append({"id": cat_id, "label": cat_label, "skills": skills})
    return {"categories": categories}


@router.post("/api/config/skills/update")
async def config_skills_update(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    disabled = body.get("disabled", [])
    if not isinstance(disabled, list):
        return JSONResponse(status_code=400, content={"error": "disabled must be an array"})

    _DISABLED_SKILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DISABLED_SKILLS_PATH.write_text(
        json5.dumps(disabled, indent=2) + "\n", encoding="utf-8"
    )

    bin_dir = _REPO_ROOT / "core" / "bin"
    skill_verify_paths: List[str] = []
    for _, _, cat_dir in _SKILL_CATEGORIES:
        if cat_dir.is_dir():
            for child in sorted(cat_dir.iterdir()):
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_verify_paths.append(str(child))

    commands: List[tuple[str, List[str]]] = [
        ("skill-verify", [str(bin_dir / "skill-verify")] + skill_verify_paths),
        ("skill-install", [str(bin_dir / "skill-install")]),
    ]

    results: List[Dict[str, Any]] = []
    for cmd_name, cmd_args in commands:
        if cmd_name == "skill-verify" and not skill_verify_paths:
            results.append({"command": cmd_name, "exit_code": 0, "output": "No skills to verify (skipped)"})
            continue
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd_args,
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                timeout=120,
                shell=False,
                env=safe_env(),
            )
            results.append({
                "command": cmd_name,
                "exit_code": proc.returncode,
                "output": (proc.stdout or "") + (proc.stderr or ""),
            })
        except subprocess.TimeoutExpired:
            results.append({"command": cmd_name, "exit_code": -1, "output": "Timed out after 120s"})
        except Exception as exc:
            results.append({"command": cmd_name, "exit_code": -1, "output": str(exc)})

    return {"status": "ok", "results": results}


def _find_skill_category_dir(category: str) -> Path | None:
    for cat_id, _, cat_dir in _SKILL_CATEGORIES:
        if cat_id == category:
            return cat_dir
    return None


@router.get("/api/config/skills/{category}/{name}/content")
def config_skill_content_read(category: str, name: str):
    cat_dir = _find_skill_category_dir(category)
    if cat_dir is None:
        return JSONResponse(status_code=404, content={"error": f"Unknown category: {category}"})
    skill_md = cat_dir / name / "SKILL.md"
    if not skill_md.is_file():
        return JSONResponse(status_code=404, content={"error": f"Skill not found: {category}/{name}"})
    content = skill_md.read_text(encoding="utf-8", errors="replace")
    return {"content": content}


@router.post("/api/config/skills/{category}/{name}/content")
async def config_skill_content_write(category: str, name: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    content = body.get("content")
    if content is None:
        return JSONResponse(status_code=400, content={"error": "content is required"})

    cat_dir = _find_skill_category_dir(category)
    if cat_dir is None:
        return JSONResponse(status_code=404, content={"error": f"Unknown category: {category}"})
    skill_dir = cat_dir / name
    skill_md = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        return JSONResponse(status_code=404, content={"error": f"Skill not found: {category}/{name}"})

    skill_md.write_text(content, encoding="utf-8")

    bin_dir = _REPO_ROOT / "core" / "bin"
    results: List[Dict[str, Any]] = []
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [str(bin_dir / "skill-verify"), str(skill_dir)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=120,
            shell=False,
            env=safe_env(),
        )
        results.append({
            "command": "skill-verify",
            "exit_code": proc.returncode,
            "output": (proc.stdout or "") + (proc.stderr or ""),
        })
    except subprocess.TimeoutExpired:
        results.append({"command": "skill-verify", "exit_code": -1, "output": "Timed out after 120s"})
    except Exception as exc:
        results.append({"command": "skill-verify", "exit_code": -1, "output": str(exc)})

    return {"status": "ok", "results": results}


@router.post("/api/config/mcp-servers/sync")
async def config_mcp_servers_sync():
    bin_dir = _REPO_ROOT / "core" / "bin"
    skill_verify_paths: List[str] = []
    for skills_dir in (_MCP_SKILLS_DIR, _SYSTEM_SKILLS_DIR):
        if skills_dir.is_dir():
            for child in sorted(skills_dir.iterdir()):
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_verify_paths.append(str(child))

    results: List[Dict[str, Any]] = []

    # 1) Sync MCP in-process (do not shell out to core/bin/sync-mcp).
    try:
        from mcp_servers.mcp_to_skills.sync import sync_mcp_tools

        summary = await asyncio.to_thread(sync_mcp_tools, repo_root=_REPO_ROOT)
        output_lines: list[str] = []
        output_lines.append(f"Synced {summary.get('total_tools', 0)} tools.")
        synced = summary.get("synced_servers") or []
        skipped = summary.get("skipped_servers") or []
        if synced:
            output_lines.append("Servers synced:")
            for line in synced:
                output_lines.append(f"  - {line}")
        if skipped:
            output_lines.append("Skipped:")
            for line in skipped:
                output_lines.append(f"  - {line}")
        results.append({"command": "sync-mcp (in-process)", "exit_code": 0, "output": "\n".join(output_lines) + "\n"})
    except Exception as exc:
        results.append({"command": "sync-mcp (in-process)", "exit_code": -1, "output": str(exc)})
        return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    # 2) Verify generated skills (still uses core/bin scripts).
    if not skill_verify_paths:
        results.append({"command": "skill-verify", "exit_code": 0, "output": "No skills to verify (skipped)"})
    else:
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [str(bin_dir / "skill-verify"), *skill_verify_paths],
                capture_output=True,
                text=True,
                cwd=str(_REPO_ROOT),
                timeout=120,
                shell=False,
                env=safe_env(),
            )
            results.append({
                "command": "skill-verify",
                "exit_code": proc.returncode,
                "output": (proc.stdout or "") + (proc.stderr or ""),
            })
            if proc.returncode != 0:
                return JSONResponse(status_code=500, content={
                    "error": f"skill-verify failed with exit code {proc.returncode}",
                    "results": results,
                })
        except subprocess.TimeoutExpired:
            results.append({"command": "skill-verify", "exit_code": -1, "output": "Timed out after 120s"})
            return JSONResponse(status_code=500, content={"error": "skill-verify timed out", "results": results})
        except Exception as exc:
            results.append({"command": "skill-verify", "exit_code": -1, "output": str(exc)})
            return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    # 3) Install skills.
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [str(bin_dir / "skill-install")],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=120,
            shell=False,
            env=safe_env(),
        )
        results.append({
            "command": "skill-install",
            "exit_code": proc.returncode,
            "output": (proc.stdout or "") + (proc.stderr or ""),
        })
        if proc.returncode != 0:
            return JSONResponse(status_code=500, content={
                "error": f"skill-install failed with exit code {proc.returncode}",
                "results": results,
            })
    except subprocess.TimeoutExpired:
        results.append({"command": "skill-install", "exit_code": -1, "output": "Timed out after 120s"})
        return JSONResponse(status_code=500, content={"error": "skill-install timed out", "results": results})
    except Exception as exc:
        results.append({"command": "skill-install", "exit_code": -1, "output": str(exc)})
        return JSONResponse(status_code=500, content={"error": str(exc), "results": results})

    return {"status": "ok", "results": results}


@router.get("/api/config/schedules")
def config_schedules_list():
    from scheduler import load_schedules
    try:
        schedules = load_schedules()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "schedules": []})
    return {"schedules": schedules}


@router.post("/api/config/schedules")
async def config_schedules_save(request: Request):
    from scheduler import load_schedules, save_schedules, reload_scheduler
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    schedule_id = (str(body.get("id") or "")).strip()
    name = (str(body.get("name") or "")).strip()
    skill = (str(body.get("skill") or "")).strip()
    cron = (str(body.get("cron") or "")).strip()
    provider = (str(body.get("provider") or "")).strip()
    enabled = body.get("enabled", True)

    if not name:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    if not skill:
        return JSONResponse(status_code=400, content={"error": "skill is required"})
    if not cron:
        return JSONResponse(status_code=400, content={"error": "cron is required"})

    try:
        CronTrigger.from_crontab(cron)
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=400, content={"error": f"Invalid cron expression: {exc}"})

    schedules = load_schedules()

    entry = {
        "id": schedule_id or secrets.token_hex(4),
        "name": name,
        "skill": skill,
        "cron": cron,
        "provider": provider,
        "enabled": bool(enabled),
    }

    if schedule_id:
        found = False
        for i, existing in enumerate(schedules):
            if existing.get("id") == schedule_id:
                schedules[i] = entry
                found = True
                break
        if not found:
            schedules.append(entry)
    else:
        schedules.append(entry)

    try:
        save_schedules(schedules)
        reload_scheduler()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok", "schedule": entry}


@router.delete("/api/config/schedules/{schedule_id}")
def config_schedules_delete(schedule_id: str):
    from scheduler import load_schedules, save_schedules, reload_scheduler

    schedule_id = schedule_id.strip()
    if not schedule_id:
        return JSONResponse(status_code=400, content={"error": "Schedule ID is required"})

    schedules = load_schedules()
    original_len = len(schedules)
    schedules = [s for s in schedules if s.get("id") != schedule_id]

    if len(schedules) == original_len:
        return JSONResponse(status_code=404, content={"error": f"Schedule not found: {schedule_id}"})

    try:
        save_schedules(schedules)
        reload_scheduler()
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok"}


@router.websocket("/api/terminal/ws")
async def terminal_ws(
    websocket: WebSocket,
    command: str = Query("top"),
    session: str | None = Query(None),
    cols: int = Query(120),
    rows: int = Query(30),
    binary: int = Query(0),
    readonly: int = Query(0),
):
    started_at = time.perf_counter()
    await websocket.accept()

    is_readonly = int(readonly or 0) == 1
    session_name: str | None = None
    if session:
        try:
            if is_readonly:
                session_name = _validate_tmux_session_name_any(session)
            else:
                session_name = _validate_tmux_session_name(session)
        except ValueError as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1008)
            return
        try:
            if not _tmux_session_exists(session_name):
                await websocket.send_text(json.dumps({"type": "error", "error": f"tmux session not found: {session_name}"}))
                await websocket.close(code=1008)
                return
        except RuntimeError as exc:
            await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
            await websocket.close(code=1011)
            return
        if is_readonly:
            shell_command = _build_tmux_attach_command_any(session_name, readonly=True)
        else:
            shell_command = _build_tmux_attach_command(session_name)
    else:
        shell_command = _coerce_command(command)

    use_binary = int(binary or 0) == 1
    initial_cols = max(20, min(int(cols or 120), 500))
    initial_rows = max(5, min(int(rows or 30), 200))
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(
        "[terminal-ws] accepted client=%s command=%s session=%s cols=%s rows=%s",
        client_host,
        shell_command,
        session_name or "",
        initial_cols,
        initial_rows,
    )
    master_fd, slave_fd = pty.openpty()
    proc: subprocess.Popen[Any] | None = None

    try:
        _set_pty_size(master_fd, initial_cols, initial_rows)
        _set_pty_size(slave_fd, initial_cols, initial_rows)
        def _child_preexec() -> None:
            # Mirror node-pty behavior: child gets a new session and controlling TTY.
            os.setsid()
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except OSError:
                pass

        proc = subprocess.Popen(
            ["/bin/sh", "-lc", shell_command],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=False,
            preexec_fn=_child_preexec,
            env=safe_env(
                extra={
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
                "COLUMNS": str(initial_cols),
                "LINES": str(initial_rows),
                }
            ),
            close_fds=True,
        )
    except Exception as exc:
        os.close(master_fd)
        os.close(slave_fd)
        await websocket.send_text(json.dumps({"type": "error", "error": str(exc)}))
        await websocket.close(code=1011)
        return
    user_input_event = asyncio.Event()
    output_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def reader() -> None:
        try:
            while True:
                chunk = await asyncio.to_thread(os.read, master_fd, 8192)
                if not chunk:
                    break
                await output_queue.put(chunk)
        except OSError:
            pass
        finally:
            await output_queue.put(None)

    async def sender() -> None:
        max_size = 262144
        flush_delay = 0.003
        buffer: list[bytes] = []
        buffered_len = 0
        image_url_cache: Dict[bytes, bytes] = {}

        async def flush() -> None:
            nonlocal buffered_len
            if not buffer:
                return
            payload = b"".join(buffer)
            buffer.clear()
            buffered_len = 0
            if TERMINAL_AUTO_IMAGE_URL_PREVIEW:
                payload = await _replace_image_urls_with_iip(payload, image_url_cache)
            if use_binary:
                await websocket.send_bytes(payload)
            else:
                await websocket.send_text(json.dumps({"type": "output", "data": payload.decode(errors="replace")}))

        while True:
            try:
                if buffer:
                    item = await asyncio.wait_for(output_queue.get(), timeout=flush_delay)
                else:
                    item = await output_queue.get()
            except asyncio.TimeoutError:
                await flush()
                continue

            if item is None:
                await flush()
                break

            buffer.append(item)
            buffered_len += len(item)
            if buffered_len >= max_size or user_input_event.is_set():
                user_input_event.clear()
                await flush()

    async def receiver() -> None:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = {"type": "input", "data": message}
            event_type = payload.get("type")
            if event_type == "resize":
                next_cols = int(payload.get("cols") or 120)
                next_rows = int(payload.get("rows") or 30)
                _set_pty_size(master_fd, next_cols, next_rows)
                _set_pty_size(slave_fd, next_cols, next_rows)
                _notify_sigwinch(master_fd, proc)
                continue
            if event_type == "input":
                if is_readonly:
                    continue
                data = str(payload.get("data") or "")
                if data:
                    await asyncio.to_thread(os.write, master_fd, data.encode())
                    user_input_event.set()
                continue
            if event_type == "close":
                break

    reader_task = asyncio.create_task(reader())
    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        done, pending = await asyncio.wait(
            [reader_task, sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        if proc is not None:
            await _terminate_process(proc)
        try:
            os.close(master_fd)
        except OSError:
            pass
        try:
            os.close(slave_fd)
        except OSError:
            pass
        try:
            await websocket.close()
        except RuntimeError:
            pass
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "[terminal-ws] closed client=%s command=%s session=%s elapsed_ms=%s",
            client_host,
            shell_command,
            session_name or "",
            elapsed_ms,
        )

@router.get("/api/courses/tree")
def courses_tree():
    if not COURSES_DIR.exists():
        return {"items": []}
    return {"items": build_tree(COURSES_DIR)}


@router.get("/api/courses/latest")
def courses_latest():
    if not COURSES_DIR.exists():
        return {"path": None}
    latest = find_latest_course(COURSES_DIR)
    if not latest:
        return {"path": None}
    return {"path": latest[0]}


@router.get("/api/courses/content")
def course_content(course: str):
    file_path = safe_course_path(course)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    meta = read_course_meta(content)
    return {"path": course, "content": content, "meta": meta}


@router.post("/api/courses/reset")
def reset_course_progress(payload: Dict[str, Any]):
    course = payload.get("course")
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"last_step": 0})
    file_path.write_text(updated, encoding="utf-8")
    return {"status": "ok"}


@router.post("/api/courses/save")
def save_course_content(payload: Dict[str, Any]):
    course = payload.get("course")
    content = payload.get("content")
    if course is None:
        return JSONResponse(status_code=400, content={"error": "Missing course path"})
    if not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "Invalid content"})
    file_path = safe_course_path(course)
    file_path.write_text(content, encoding="utf-8")
    return {"status": "ok"}


def _write_text_atomic(path: Path, text: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_new_workflow_file_with_collision_retry(target_dir: Path, filename: str, content_text: str) -> Path:
    if not filename.endswith(".json"):
        filename = normalize_workflow_filename(filename)
    if not is_valid_workflow_filename(filename):
        raise ValueError("Invalid workflow filename")

    base = filename[:-5]
    candidate = filename
    index = 2
    while True:
        candidate_path = target_dir / candidate
        try:
            with candidate_path.open("x", encoding="utf-8") as fh:
                fh.write(content_text)
            return candidate_path
        except FileExistsError:
            candidate = f"{base}-{index}.json"
            index += 1


@router.get("/api/workflows/tree")
def workflows_tree():
    if not WORKFLOWS_DIR.exists():
        return {"items": []}
    return {"items": build_workflow_tree(WORKFLOWS_DIR, WORKFLOWS_DIR)}


@router.get("/api/workflows/latest")
def workflows_latest():
    if not WORKFLOWS_DIR.exists():
        return {"path": None}
    latest = find_latest_workflow(WORKFLOWS_DIR)
    return {"path": latest}


@router.get("/api/workflows/content")
def workflows_content(workflow: str):
    file_path = safe_workflow_path(WORKFLOWS_DIR, workflow)
    try:
        content = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid workflow JSON"})
    if not isinstance(content, dict):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid workflow document",
                "errors": [
                    {
                        "rule": "SHAPE_WORKFLOW",
                        "message": "`workflow` must be an object.",
                        "node_ids": [],
                        "edge_ids": [],
                    }
                ],
            },
        )
    errors = validate_workflow_doc(content)
    if errors:
        return JSONResponse(status_code=400, content={"error": "Invalid workflow document", "errors": errors})
    return {"path": workflow, "content": content}


@router.post("/api/workflows/validate")
def workflows_validate(payload: Dict[str, Any]):
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return JSONResponse(status_code=400, content={"valid": False, "errors": [{"rule": "SHAPE_WORKFLOW", "message": "`workflow` must be an object.", "node_ids": [], "edge_ids": []}]})
    errors = validate_workflow_doc(workflow)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/api/workflows/save")
def workflows_save(payload: Dict[str, Any]):
    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        return JSONResponse(status_code=400, content={"status": "error", "valid": False, "errors": [{"rule": "SHAPE_WORKFLOW", "message": "`workflow` must be an object.", "node_ids": [], "edge_ids": []}]})

    errors = validate_workflow_doc(workflow)
    if errors:
        return JSONResponse(status_code=400, content={"status": "error", "valid": False, "errors": errors})

    existing_path_raw = str(payload.get("path") or "").strip()
    existing_file: Path | None = None
    if existing_path_raw:
        existing_file = safe_workflow_path(WORKFLOWS_DIR, existing_path_raw)

    raw_filename = str(payload.get("filename") or "").strip()
    if existing_file is not None and not raw_filename:
        filename = existing_file.name
    elif raw_filename:
        if not raw_filename.endswith(".json"):
            raw_filename = f"{raw_filename}.json"
        if not is_valid_workflow_filename(raw_filename):
            normalized = normalize_workflow_filename(raw_filename[:-5] if raw_filename.endswith(".json") else raw_filename)
            filename = normalized
        else:
            filename = raw_filename
    else:
        filename = normalize_workflow_filename(str(workflow.get("name") or "workflow"))

    target_dir = existing_file.parent if existing_file is not None else WORKFLOWS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    desired_path = target_dir / filename
    to_save = dict(workflow)
    to_save["version"] = str(to_save.get("version") or "1.0")
    to_save["updated_at"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    payload_text = json.dumps(to_save, indent=2) + "\n"

    if existing_file is not None and desired_path.resolve() == existing_file.resolve():
        final_path = existing_file
        _write_text_atomic(final_path, payload_text)
    else:
        try:
            final_path = _write_new_workflow_file_with_collision_retry(target_dir, filename, payload_text)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "valid": False,
                    "errors": [{"rule": "FILENAME", "message": str(exc), "node_ids": [], "edge_ids": []}],
                },
            )

    saved_rel_path = str(final_path.relative_to(WORKFLOWS_DIR))
    return {"status": "ok", "path": saved_rel_path, "saved_name": final_path.name}


@router.get("/api/llm/providers")
def llm_providers():
    providers = load_llm_providers()
    return {
        "providers": [{"id": p.get("id"), "name": p.get("name")} for p in providers],
        "default": get_default_llm_provider_id(),
    }


@router.post("/api/llm/stop")
def llm_stop(payload: Dict[str, Any]):
    return {"status": stop_client(payload.get("client_id"))}


@router.post("/rest/assignment-last-step")
def assignment_last_step(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    last_step = payload.get("last_step")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"last_step": int(last_step or 0)})
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/assignment-web-url")
def assignment_web_url(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    web_url = payload.get("web_url")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, {"web_url": web_url})
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/assignment-activity")
def assignment_activity(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updates = {"last_activity": payload, "last_step": payload.get("currentStep")}
    updated = write_course_meta(text, updates)
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/submit-assignment")
def submit_assignment(payload: Dict[str, Any]):
    course = payload.get("assignment_token")
    if course is None:
        return {"payload": None, "error": "The task does not exist!"}
    updates = {
        "result": payload.get("content"),
        "status": payload.get("status"),
        "feedback": payload.get("feedback"),
        "testResults": payload.get("testResults"),
        "submit_time": datetime.utcnow().isoformat(),
        "last_step": payload.get("currentStep"),
    }
    file_path = safe_course_path(course)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    updated = write_course_meta(text, updates)
    file_path.write_text(updated, encoding="utf-8")
    return {"payload": "OK", "error": None}


@router.post("/rest/tikzjax")
def tikzjax(_: Dict[str, Any]):
    return JSONResponse(status_code=501, content={"payload": None, "error": "tikzjax not configured"})


@router.post("/rest/code_v1")
async def rest_code_v1(request: Request):
    data = await request.json()
    message = data.get("message", "")
    lang = data.get("lang")
    extra = data.get("extraInfo")
    provider_id = data.get("provider")
    client_id = data.get("client_id") or request.headers.get("x-client-id") or request.client.host
    auto_allow = _bool_with_default(data.get("auto_allow"), False)
    network_allow = _bool_with_default(data.get("network_allow"), False)
    sandbox_mode = _bool_with_default(data.get("sandbox_mode"), True)
    system_message = build_code_system_message(message, lang or "any")
    prompt = f"{system_message}\n\nUser:\n{message}"
    if extra:
        prompt = f"{prompt}\n\nExtra Info:\n{extra}"
    if lang:
        prompt = f"Language: {lang}\n{prompt}"
    return StreamingResponse(
        llm_stream(
            prompt,
            provider_id,
            client_id,
            auto_allow=auto_allow,
            network_allow=network_allow,
            sandbox_mode=sandbox_mode,
        ),
        media_type="text/plain",
    )


@router.post("/rest/chat")
async def rest_chat(request: Request):
    data = await request.json()
    message = data.get("message", "")
    extra = data.get("extraInfo")
    to_lang = data.get("toLang")
    lang = data.get("lang") or "any"
    provider_id = data.get("provider")
    client_id = data.get("client_id") or request.headers.get("x-client-id") or request.client.host
    auto_allow = _bool_with_default(data.get("auto_allow"), False)
    network_allow = _bool_with_default(data.get("network_allow"), False)
    sandbox_mode = _bool_with_default(data.get("sandbox_mode"), True)

    if to_lang:
        system_message = build_translate_system_message(lang, to_lang)
    else:
        system_message = build_chat_system_message()

    prompt = f"{system_message}\n\nUser:\n{message}"
    if extra:
        prompt = f"{prompt}\n\nExtra Info:\n{extra}"

    return StreamingResponse(
        llm_stream(
            prompt,
            provider_id,
            client_id,
            auto_allow=auto_allow,
            network_allow=network_allow,
            sandbox_mode=sandbox_mode,
        ),
        media_type="text/plain",
    )


@router.post("/rest/audio")
async def rest_audio(
    file: UploadFile = File(None),
    action: str = Form(None),
    provider: str = Form(None),
    client_id: str = Form(None),
):
    _ = file
    _ = action
    _ = provider
    _ = client_id
    return StreamingResponse(iter([b"[-ERROR-]"]), media_type="text/plain")


@router.post("/api/execute_code")
async def execute_code(request: Request):
    data = await request.json()
    lang = data.get("lang")
    meta = data.get("meta")
    source = data.get("source")
    client_ip = request.client.host if request.client else "local"

    result = execute_code_impl(lang, meta, source, client_ip)
    return {"data": {"execute_code": result}}


@router.post("/api/vscode/event")
async def vscode_event(payload: Dict[str, Any]):
    local_dev_token = str(payload.get("local_dev_token") or LOCAL_DEV_TOKEN or "").strip()
    event_payload = payload.get("payload")

    if not local_dev_token:
        return JSONResponse(
            status_code=400,
            content={"payload": None, "error": "local_dev_token is required"},
        )
    if not isinstance(event_payload, dict):
        return JSONResponse(
            status_code=400,
            content={"payload": None, "error": "payload must be a JSON object"},
        )

    sent_count = await emit_to_vscode_clients(local_dev_token, event_payload)
    if sent_count <= 0:
        return JSONResponse(
            status_code=404,
            content={"payload": None, "error": "No VS Code extension clients connected for this local_dev_token"},
        )

    return {"payload": {"sent": sent_count}, "error": None}


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {"authenticated": _is_authorized_request(request)}


@router.post("/api/auth/session")
async def auth_session(request: Request):
    data = await request.json()
    provided = _sanitize_single_line_secret(str(data.get("auth_token") or ""))
    expected = _sanitize_single_line_secret(get_auth_token())
    if not provided:
        return JSONResponse(status_code=400, content={"error": "auth_token is required"})
    if not expected or not secrets.compare_digest(provided, expected):
        return JSONResponse(status_code=401, content={"error": "invalid auth token"})

    response = JSONResponse(content={"status": "ok", "message": "Authenticated"})
    response.set_cookie(
        key=_AUTH_COOKIE_NAME,
        value=expected,
        httponly=True,
        secure=get_only_allow_https(),
        samesite="lax",
        path="/",
        max_age=_AUTH_COOKIE_MAX_AGE,
    )
    return response


@router.post("/api/discord/broadcast")
async def discord_broadcast(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    data = await request.json()
    message_text = (str(data.get("message") or "")).strip()
    if not message_text:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    from discord_bot import send_dm_to_all
    count = await send_dm_to_all(message_text)
    return {"status": "ok", "sent_count": count}


@router.get("/api/discord/status")
def discord_status(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    has_token = bool(get_discord_bot_token())
    connected = False
    bot_name = None
    guild_count = 0
    if has_token:
        try:
            from discord_bot import bot
            connected = bot.is_ready()
            if connected and bot.user:
                bot_name = str(bot.user)
                guild_count = len(bot.guilds)
        except Exception:
            pass
    keys_safe_guard_enabled = os.getenv("IN_KEYS_SAFE_GUARD", "").strip() == "1"
    return {
        "has_token": has_token,
        "connected": connected,
        "bot_name": bot_name,
        "guild_count": guild_count,
        "keys_safe_guard_enabled": keys_safe_guard_enabled,
    }


@router.get("/api/discord/sessions")
def discord_sessions_list(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    from discord_session import SessionManager
    mgr = SessionManager()
    return {"sessions": mgr.list_sessions()}


@router.get("/api/discord/sessions/{channel_id}")
def discord_session_history(channel_id: str, request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    from discord_session import ChatSession
    session = ChatSession(channel_id)
    history = session.get_full_history()
    return {"channel_id": channel_id, "messages": history}


@router.get("/api/live-avatar/config")
def live_avatar_config(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    return JSONResponse({
        "live_avatar_ws_url": get_live_avatar_server_url(),
        "turn_server_urls": get_turn_server_urls(),
        "turn_server_username": get_turn_server_username(),
        "turn_server_password": get_turn_server_password(),
    })


@router.get("/api/cameras/config")
def cameras_config(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    return JSONResponse({
        "turn_server_urls": get_turn_server_urls(),
        "turn_server_username": get_turn_server_username(),
        "turn_server_password": get_turn_server_password(),
    })


# ── Cameras MCP client (lazy singleton) ──────────────────────────────────────
_cameras_mcp_client = None
_cameras_mcp_lock = asyncio.Lock()
_cameras_signal_tool_lock = asyncio.Lock()


async def _get_cameras_client():
    """Return a live StdioClient for the cameras MCP server, creating it on first call."""
    global _cameras_mcp_client
    async with _cameras_mcp_lock:
        if _cameras_mcp_client is not None:
            # Check if the subprocess is still alive
            proc = getattr(_cameras_mcp_client, "_process", None)
            if proc is not None and proc.poll() is None:
                return _cameras_mcp_client
        # (Re)create the client
        from mcp_servers.mcp_to_skills.sync import create_client, load_mcp_configs, is_server_enabled
        configs, _ = await asyncio.to_thread(load_mcp_configs, _MCP_CONFIG_PATH)
        cam_cfg = configs.get("cameras")
        if cam_cfg is None:
            raise RuntimeError("cameras MCP server not found in config/mcp.json5")
        if not is_server_enabled(cam_cfg):
            raise RuntimeError("cameras MCP server is disabled — enable it in MCP settings first")
        _cameras_mcp_client = await asyncio.to_thread(create_client, cam_cfg)
        return _cameras_mcp_client


async def _reset_cameras_client() -> None:
    global _cameras_mcp_client
    async with _cameras_mcp_lock:
        client = _cameras_mcp_client
        _cameras_mcp_client = None
    if client is not None:
        try:
            await asyncio.to_thread(client.close)
        except Exception:
            pass


async def _call_cameras_tool(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    timeout_seconds: float = 20.0,
    retry_timeouts: tuple[float, float] | None = None,
) -> Any:
    """Call a cameras MCP tool with timeout and one automatic client-reset retry."""
    async with _cameras_signal_tool_lock:
        last_exc: Exception | None = None
        for _attempt in (1, 2):
            current_timeout = (
                retry_timeouts[_attempt - 1]
                if retry_timeouts is not None
                else timeout_seconds
            )
            started = time.monotonic()
            try:
                client = await _get_cameras_client()
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.request,
                        "tools/call",
                        {"name": tool_name, "arguments": arguments},
                    ),
                    timeout=current_timeout,
                )
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.info(
                    "[cameras.signal] tool=%s attempt=%d ok elapsed_ms=%d timeout_ms=%d",
                    tool_name,
                    _attempt,
                    elapsed_ms,
                    int(current_timeout * 1000),
                )
                return result
            except Exception as exc:
                last_exc = exc
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.warning(
                    "[cameras.signal] tool=%s attempt=%d failed elapsed_ms=%d timeout_ms=%d error=%s",
                    tool_name,
                    _attempt,
                    elapsed_ms,
                    int(current_timeout * 1000),
                    exc,
                )
                await _reset_cameras_client()
        if last_exc is None:
            raise RuntimeError("Unknown cameras MCP call error")
        raise last_exc


@router.post("/api/cameras/signal")
async def cameras_signal(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    signal_type = body.get("type", "")
    req_started = time.monotonic()
    logger.info("[cameras.signal] recv type=%s", signal_type)
    try:
        client = await _get_cameras_client()
    except RuntimeError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})

    if signal_type == "offer":
        def _normalize_sdp_answer(payload: Any) -> dict[str, Any] | Any:
            if not isinstance(payload, dict):
                return payload
            # Some MCP tool wrappers return {"result":"{...json...}"} (or nested dict).
            # Unwrap that shape first so WebUI always receives top-level sdp/type.
            if "result" in payload and ("sdp" not in payload and "type" not in payload and "sdpType" not in payload):
                result_payload = payload.get("result")
                if isinstance(result_payload, str):
                    try:
                        decoded = json.loads(result_payload)
                        if isinstance(decoded, dict):
                            payload = decoded
                    except json.JSONDecodeError:
                        pass
                elif isinstance(result_payload, dict):
                    payload = result_payload
            answer_type = payload.get("type")
            if not isinstance(answer_type, str) or not answer_type:
                if isinstance(payload.get("sdpType"), str) and payload.get("sdpType"):
                    payload["type"] = payload["sdpType"]
                elif isinstance(payload.get("sdp_type"), str) and payload.get("sdp_type"):
                    payload["type"] = payload["sdp_type"]
            if isinstance(payload.get("type"), str) and payload.get("type") and "sdpType" not in payload:
                payload["sdpType"] = payload["type"]
            return payload

        sdp = body.get("sdp", "")
        sdp_type = body.get("sdpType", "offer")
        is_ice_restart = bool(body.get("iceRestart", False))
        candidates = body.get("candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        if not sdp:
            return JSONResponse(status_code=400, content={"error": "sdp is required"})
        try:
            result_raw = await _call_cameras_tool(
                "webrtc_offer",
                {
                    "sdp": sdp,
                    "sdp_type": sdp_type,
                    "candidates": candidates,
                },
                timeout_seconds=6.0,
                retry_timeouts=(2.5, 6.0) if is_ice_restart else None,
            )
        except Exception as exc:
            logger.warning("[cameras.signal] offer failed error=%s", exc)
            return JSONResponse(status_code=502, content={"error": f"cameras MCP webrtc_offer failed: {exc}"})
        # Accept both structuredContent and text content from MCP responses.
        if not isinstance(result_raw, dict):
            return JSONResponse(status_code=502, content={"error": "Invalid cameras MCP response"})
        if isinstance(result_raw.get("structuredContent"), dict):
            return JSONResponse(_normalize_sdp_answer(result_raw["structuredContent"]))
        if isinstance(result_raw.get("sdp"), str) and isinstance(result_raw.get("type"), str):
            return JSONResponse({"sdp": result_raw["sdp"], "type": result_raw["type"]})

        content = result_raw.get("content")
        text = ""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    candidate = item.get("text")
                    if isinstance(candidate, str) and candidate.strip():
                        text = candidate
                        break
        if bool(result_raw.get("isError")):
            detail = text or "Unknown cameras MCP tool error"
            return JSONResponse(status_code=502, content={"error": detail})
        if not text:
            return JSONResponse(
                status_code=502,
                content={"error": "Empty cameras MCP response for webrtc_offer"},
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=502,
                content={"error": "Invalid JSON from cameras MCP webrtc_offer", "raw": text[:300]},
            )
        if not isinstance(parsed, dict):
            return JSONResponse(status_code=502, content={"error": "Unexpected webrtc_offer response shape"})
        normalized = _normalize_sdp_answer(parsed)
        elapsed_ms = int((time.monotonic() - req_started) * 1000)
        cand_count = len(normalized.get("candidates", [])) if isinstance(normalized, dict) and isinstance(normalized.get("candidates"), list) else 0
        logger.info("[cameras.signal] offer ok elapsed_ms=%d answer_candidates=%d", elapsed_ms, cand_count)
        return JSONResponse(normalized)

    elif signal_type == "ice_candidate":
        candidate = body.get("candidate", {})
        if not candidate:
            return JSONResponse(status_code=400, content={"error": "candidate is required"})
        try:
            ice_result = await _call_cameras_tool(
                "webrtc_ice_candidate",
                {
                    "candidate": candidate.get("candidate", ""),
                    "sdp_mid": candidate.get("sdpMid", ""),
                    "sdp_mline_index": int(candidate.get("sdpMLineIndex", 0)),
                },
                timeout_seconds=4.0,
            )
        except Exception as exc:
            logger.warning("[cameras.signal] ice_candidate failed error=%s", exc)
            return JSONResponse(status_code=502, content={"error": f"cameras MCP webrtc_ice_candidate failed: {exc}"})
        if isinstance(ice_result, dict) and bool(ice_result.get("isError")):
            content = ice_result.get("content")
            detail = "Unknown cameras MCP tool error"
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if isinstance(text, str) and text.strip():
                            detail = text
                            break
            return JSONResponse(status_code=502, content={"error": detail})
        elapsed_ms = int((time.monotonic() - req_started) * 1000)
        logger.info("[cameras.signal] ice_candidate ok elapsed_ms=%d", elapsed_ms)
        return JSONResponse({"status": "ok"})

    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown signal type: {signal_type}"})


@router.post("/api/webui/log")
async def webui_log(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "payload must be an object"})

    tag = str(payload.get("tag") or "webui").replace("\n", " ").replace("\r", " ").strip()
    level = str(payload.get("level") or "info").lower()
    message = str(payload.get("message") or "").replace("\n", " ").replace("\r", " ").strip()
    data = payload.get("data")

    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    line = f"[{tag}] {message}"
    if data is not None:
        line = f"{line} data={data!r}"

    if level in {"error"}:
        logger.error(line)
    elif level in {"warn", "warning"}:
        logger.warning(line)
    elif level in {"debug"}:
        logger.debug(line)
    else:
        logger.info(line)
    return JSONResponse({"status": "ok"})


@router.post("/api/internal/discord/notify")
async def internal_discord_notify(request: Request):
    """Internal endpoint for cameras MCP server to send Discord DMs with detection images."""
    # Only allow requests from localhost
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    message = str(body.get("message", ""))
    image_path = str(body.get("image_path", ""))
    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})
    try:
        from discord_bot import bot, send_dm_to_all
        if bot.is_ready():
            sent = await send_dm_to_all(message, image_path=image_path or None)
            return JSONResponse({"status": "ok", "sent": sent})
        else:
            return JSONResponse({"status": "skipped", "reason": "Discord bot not ready"})
    except Exception as exc:
        logger.warning("Discord notify error: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/discord/token")
async def discord_token_save(request: Request):
    if not _is_authorized_request(request):
        return _auth_required_response()
    data = await request.json()
    token = _sanitize_single_line_secret(str(data.get("token") or ""))
    if not token:
        return JSONResponse(status_code=400, content={"error": "token is required"})

    keys_safe_guard = str(PROJECT_DIR / "core" / "bin" / "keys-safe-guard")
    cmd = [keys_safe_guard]
    if os.getenv("IN_KEYS_SAFE_GUARD", "").strip() == "1":
        # config/.env is root-owned — request GUI elevation dialog.
        cmd.append("--gui")
    cmd += ["put_key_values", f"DISCORD_BOT_TOKEN={token}"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("keys-safe-guard failed: %s", result.stderr)
        return JSONResponse(
            status_code=500,
            content={
                "error": (
                    "Could not save token: GUI auth dialog unavailable, failed, or was cancelled. "
                    "To set the token manually, run as root:\n"
                    "  sudo nano config/.env\n"
                    "then add or update the line:\n"
                    "  DISCORD_BOT_TOKEN=<your-token>"
                )
            },
        )
    # Keep the running engine environment in sync.
    os.environ["DISCORD_BOT_TOKEN"] = token

    return {"status": "ok", "message": "Token saved. Restart the engine to connect the bot."}


@router.post("/api/create_course_plan")
@router.post("/create_course_plan")
def create_course_plan(payload: Dict[str, Any]):
    requirement = str(payload.get("requirement") or "").strip()
    language = str(payload.get("language") or "English").strip() or "English"
    if not requirement:
        return JSONResponse(status_code=400, content={"error": "requirement is required"})

    course_details = COURSE_PLANNER.create_course_plan(requirement=requirement, language=language)
    return {"course_details": course_details}


@router.post("/api/create_course_video")
@router.post("/create_course_video")
def create_course_video(payload: Dict[str, Any]):
    requirement = str(payload.get("requirement") or "").strip()
    if not requirement:
        return JSONResponse(status_code=400, content={"error": "requirement is required"})

    try:
        target_duration = int(payload.get("target_duration") or 60)
    except (TypeError, ValueError):
        target_duration = 60
    resolution = str(payload.get("resolution") or "1080x1920")
    video_file_path = VIDEO_CREATOR.create_course_video(
        requirement=requirement,
        target_duration=target_duration,
        resolution=resolution,
    )
    return {"video_file_path": video_file_path}
