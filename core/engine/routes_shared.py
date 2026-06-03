import asyncio
import base64
import fcntl
import ipaddress
import json
import mimetypes
import os
import pwd
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
import threading
import time
import urllib.parse
import urllib.request
from uuid import uuid4
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from apscheduler.triggers.cron import CronTrigger

from code_executor import execute_code_impl
from course_utils import build_tree, find_latest_course, read_course_meta, safe_course_path, write_course_meta
from dev_swarm.router import router as dev_swarm_router
from file_realtime import FileRealtimeHub
import json5_io as json5
from workflow_editor_utils import (
    build_workflow_tree,
    find_latest_workflow,
    is_valid_workflow_filename,
    normalize_workflow_filename,
    safe_workflow_path,
    validate_workflow_doc,
)
from mcp_servers.mcp_to_skills.workflow_execution import (
    build_node_prompt,
    create_run_output_dir,
    load_workflow_graph,
    node_name,
    node_output_path,
    parse_instruction_file_path,
    parse_reference_file_paths,
    parse_task_workspace,
    workflow_task_output_dir,
)

from llm_service import (
    _resolve_provider_env,
    build_chat_system_message,
    build_code_system_message,
    build_llm_command,
    build_terminal_command,
    build_translate_system_message,
    format_command_for_log,
    get_default_doctor_provider_id,
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
    FEATURES_DIR,
    PROJECT_DIR,
    MEDIA_DIR,
    RESEARCH_DIR,
    SKILL_PILOT_DEVELOPMENT_DIR,
    TASKS_DIR,
    SOCIAL_MEDIA_DIR,
    VIBE_CODING_DIR,
    WORKFLOWS_DIR,
    LOCAL_DEV_TOKEN,
    TERMINAL_AUTO_IMAGE_URL_PREVIEW,
    get_auth_token,
    get_discord_bot_token,
    get_runtime_mode,
    get_service_host_port,
    get_only_allow_https,
    get_live_avatar_server_url,
    get_turn_server_urls,
    get_turn_server_username,
    get_turn_server_password,
    logger,
)
from safe_dotenv import safe_env
from session_agent_store import get_session_agent_meta, set_session_agent_meta
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
WEB_SHELL_TMUX_SESSION_PREFIX = "webui-live-sh-"
FILE_MANAGER_WEB_SHELL_SESSION_NAME = "webui-live-sh-file-manager"
NATIVE_TMUX_SESSION_PREFIX = "native-terminal-"
WORKFLOW_EXECUTE_SESSION_NAME = "sp-workflow-execute"
PROTECTED_TMUX_SESSION_PREFIXES = ("sp-engine-", "sp-webui-")
FILE_MANAGER_TERMINAL_SESSION_PREFIX = "sp-webui-file-manager-"
TMUX_SESSION_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
SAVED_TERMINAL_HISTORY_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}-[a-zA-Z0-9_-]+\.md$")
_last_heartbeat_time: float = time.time()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_CONFIG_PATH = _REPO_ROOT / "config" / "mcp.json5"
_MCP_SERVER_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_MCP_SKILLS_DIR = _REPO_ROOT / "core" / "skills" / "mcp"
_SYSTEM_SKILLS_DIR = _REPO_ROOT / "core" / "skills" / "system"
_DISABLED_SKILLS_PATH = _REPO_ROOT / "config" / "disabled_skills.json5"
_DISABLED_SUBAGENTS_PATH = _REPO_ROOT / "config" / "disabled_subagents.json5"
_EXTENSIONS_DIR = _REPO_ROOT / "extensions"
_SHOWCASES_PATH = _REPO_ROOT / "core" / "engine" / "data" / "showcases.json5"
_SKILL_CATEGORIES: List[tuple[str, str, Path]] = [
    ("system", "System", _REPO_ROOT / "core" / "skills" / "system"),
    ("dev-swarm", "Dev Swarm", _REPO_ROOT / "dev-swarm" / "skills"),
    ("mcp", "MCP", _REPO_ROOT / "core" / "skills" / "mcp"),
    ("third-party", "Third Party", _REPO_ROOT / "core" / "skills" / "third-party"),
    ("user", "User", _REPO_ROOT / "core" / "skills" / "user"),
]
_SUBAGENT_CATEGORIES: List[tuple[str, str, Path]] = [
    ("system", "System", _REPO_ROOT / "core" / "subagents" / "system"),
    ("user", "User", _REPO_ROOT / "core" / "subagents" / "user"),
]
_heartbeat_watcher_started = False
_last_native_cleanup_time: float = 0.0
_NATIVE_STALE_CLEANUP_INTERVAL_SECONDS = 60.0
_SETTINGS_PATH = _REPO_ROOT / "config" / "settings.json5"
_AI_PROVIDERS_PATH = _REPO_ROOT / "config" / "ai_providers.json5"
_CONFIG_ENV_PATH = _REPO_ROOT / "config" / ".env"
_AUTH_COOKIE_NAME = "auth_token"
_AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
_WORKFLOW_EXECUTE_LOCK = threading.Lock()
_WORKFLOW_EXECUTE_STOP = threading.Event()
_WORKFLOW_EXECUTE_CONTINUE = threading.Event()
_TERMINAL_HISTORY_KILL_LOCK = threading.Lock()
_WORKFLOW_EXECUTE_STATE: Dict[str, Any] = {
    "thread": None,
    "token": "",
    "status": "idle",
    "session_name": WORKFLOW_EXECUTE_SESSION_NAME,
    "session_managed": False,
    "workflow": "",
    "run_id": "",
    "output_root": "",
    "error": "",
    "started_at": 0.0,
    "finished_at": 0.0,
    "next_node_trigger": "auto_continue",
    "waiting_for_continue": False,
    "current_node_id": 0,
    "current_node_name": "",
    "current_output_file": "",
    "current_provider_id": "",
    "current_provider_bin": "",
    "has_remaining_nodes": False,
}


def _terminal_workflow_base_dir() -> Path:
    return _REPO_ROOT / ".skillpilot" / "temp" / "terminal-workflow"


def _terminal_histories_dir() -> Path:
    return _REPO_ROOT / ".skillpilot" / "terminal-histories"
_EXPLORE_TEMPLATE_LOCK = threading.Lock()
_EXPLORE_TEMPLATE_LAUNCHES: Dict[str, Dict[str, Any]] = {}
_EXPLORE_MANAGED_DEV: Dict[str, Any] = {
    "session_name": "sp-engine-dev",
    "worktree_path": "",
    "launch_id": "",
    "started_at": 0.0,
}

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "security": {
        "schedules": {"sandbox": True, "auto": True, "network": True},
        "newSession": {"sandbox": False, "auto": False, "network": True},
        "remoteBot": {"sandbox": True, "auto": True, "network": False},
        "devSwarm": {"sandbox": True, "auto": True, "network": True},
        "skillAgent": {},
    },
}

_EXTENSION_TYPES = {"prompt", "skill", "script"}
_EXTENSION_ACTIONS = {"install", "update", "uninstall"}


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


def _load_extension_entry(ext_dir: Path) -> Dict[str, Any] | None:
    config_path = ext_dir / "extension.json5"
    if not ext_dir.is_dir() or not config_path.is_file():
        return None

    try:
        raw = json5.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse extension config %s: %s", config_path, exc)
        return None

    if not isinstance(raw, dict):
        logger.warning("Extension config must be an object: %s", config_path)
        return None

    ext_type = str(raw.get("type") or "").strip()
    if ext_type not in _EXTENSION_TYPES:
        logger.warning("Skipping extension with invalid type %s: %s", ext_type, config_path)
        return None

    name = str(raw.get("name") or "").strip()
    description = str(raw.get("description") or "").strip()
    if not name:
        logger.warning("Skipping extension without name: %s", config_path)
        return None

    entry: Dict[str, Any] = {
        "dir": ext_dir.name,
        "name": name,
        "description": description,
        "type": ext_type,
    }

    version = str(raw.get("version") or "").strip()
    license_name = str(raw.get("license") or raw.get("licence") or "").strip()
    entrypoint = str(raw.get("entrypoint") or "").strip()
    if version:
        entry["version"] = version
    if license_name:
        entry["license"] = license_name
    installed = bool(raw.get("installed", False))
    entry["installed"] = installed
    if entrypoint:
        entry["entrypoint"] = entrypoint

    if ext_type == "prompt":
        prompt = str(raw.get("prompt") or "").strip()
        if not prompt:
            logger.warning("Skipping prompt extension without prompt key: %s", config_path)
            return None
        entry["prompt"] = prompt
    elif ext_type == "skill":
        skill = str(raw.get("skill") or "").strip()
        if not skill:
            logger.warning("Skipping skill extension without skill key: %s", config_path)
            return None
        entry["skill"] = skill
    elif ext_type == "script":
        script = str(raw.get("script") or "extension.py").strip() or "extension.py"
        entry["script"] = script

    return entry


def _list_extensions() -> List[Dict[str, Any]]:
    if not _EXTENSIONS_DIR.is_dir():
        return []

    items: List[Dict[str, Any]] = []
    for child in sorted(_EXTENSIONS_DIR.iterdir()):
        entry = _load_extension_entry(child)
        if entry is not None:
            items.append(entry)
    return items


def _find_extension(dir_name: str) -> Dict[str, Any] | None:
    for item in _list_extensions():
        if item.get("dir") == dir_name:
            return item
    return None


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


def _active_session_provider(session_name: str) -> Dict[str, Any] | None:
    session_meta = get_session_agent_meta(session_name)
    provider_id = str(session_meta.get("provider_id") or "").strip()
    if provider_id:
        try:
            return get_provider(provider_id)
        except Exception:
            pass

    provider_bin = _detect_agent_bin_for_session_any(session_name)
    if provider_bin:
        for provider in load_llm_providers():
            if str(provider.get("bin") or "").strip().lower() == provider_bin:
                return provider
    return None


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


def _resolve_system_shell() -> str:
    candidates = [
        str(os.environ.get("SHELL") or "").strip(),
    ]
    try:
        candidates.append(str(pwd.getpwuid(os.getuid()).pw_shell or "").strip())
    except Exception:
        pass
    candidates.extend(["/bin/zsh", "/bin/bash", "/bin/sh"])

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return "/bin/sh"


def _resolve_terminal_start_dir(raw_path: Any, path_mode: str | None = None) -> Path:
    value = str(raw_path or "").strip()
    if not value:
        return _REPO_ROOT
    if value == "/":
        return _REPO_ROOT

    try:
        from routes_file_manager import _file_manager_roots_by_id as _terminal_file_roots_by_id
        from routes_file_manager import _safe_files_path as _safe_terminal_files_path
    except Exception:
        _terminal_file_roots_by_id = None
        _safe_terminal_files_path = None

    if path_mode == "file_manager":
        if _safe_terminal_files_path is None:
            raise ValueError("file manager paths are not available")
        candidate = _safe_terminal_files_path(value)
        if not candidate.exists():
            raise ValueError(f"terminal path does not exist: {candidate}")
        if not candidate.is_dir():
            raise ValueError(f"terminal path is not a directory: {candidate}")
        return candidate

    if _terminal_file_roots_by_id is not None and _safe_terminal_files_path is not None:
        normalized = f"/{value.lstrip('/')}".rstrip("/") or "/"
        file_roots = _terminal_file_roots_by_id()
        # Multi-root file-manager ids are virtual paths like "/$project" or
        # "/$worktree/name". They look absolute, but should resolve through the
        # file-manager mapper before normal absolute filesystem handling.
        for root_id in sorted((root_id for root_id in file_roots if root_id != "/"), key=len, reverse=True):
            if normalized == root_id or normalized.startswith(f"{root_id}/"):
                candidate = _safe_terminal_files_path(normalized)
                if not candidate.exists():
                    raise ValueError(f"terminal path does not exist: {candidate}")
                if not candidate.is_dir():
                    raise ValueError(f"terminal path is not a directory: {candidate}")
                return candidate

    # Session root selectors send absolute filesystem paths. Resolve those
    # directly instead of feeding them through the file-manager virtual-path
    # parser, which interprets "/Users/..." as repo-relative.
    expanded_candidate = Path(os.path.expanduser(value))
    if expanded_candidate.is_absolute():
        candidate = expanded_candidate.resolve()
        if not candidate.exists():
            raise ValueError(f"terminal path does not exist: {candidate}")
        if not candidate.is_dir():
            raise ValueError(f"terminal path is not a directory: {candidate}")
        try:
            from routes_file_manager import _file_manager_root_for_absolute_path as _terminal_root_for_absolute_path
        except Exception:
            _terminal_root_for_absolute_path = None
        if _terminal_root_for_absolute_path is not None:
            if _terminal_root_for_absolute_path(candidate) is None:
                raise ValueError(f"terminal path must be inside the project or one of its worktrees: {candidate}")
        else:
            repo_root = _REPO_ROOT.resolve()
            if candidate != repo_root and repo_root not in candidate.parents:
                raise ValueError(f"terminal path must be inside the project root: {candidate}")
        return candidate

    try:
        from routes_file_manager import _file_manager_root_for_absolute_path as _terminal_root_for_absolute_path
    except Exception:
        _terminal_root_for_absolute_path = None

    if _safe_terminal_files_path is not None:
        try:
            candidate = _safe_terminal_files_path(value)
        except Exception:
            candidate = None
        if candidate is not None:
            if not candidate.exists():
                raise ValueError(f"terminal path does not exist: {candidate}")
            if not candidate.is_dir():
                raise ValueError(f"terminal path is not a directory: {candidate}")
            return candidate

    candidate = Path(os.path.expanduser(value))
    if not candidate.is_absolute():
        candidate = (_REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists():
        raise ValueError(f"terminal path does not exist: {candidate}")
    if not candidate.is_dir():
        raise ValueError(f"terminal path is not a directory: {candidate}")
    if _terminal_root_for_absolute_path is not None:
        if _terminal_root_for_absolute_path(candidate) is None:
            raise ValueError(f"terminal path must be inside the project or one of its worktrees: {candidate}")
    else:
        repo_root = _REPO_ROOT.resolve()
        if candidate != repo_root and repo_root not in candidate.parents:
            raise ValueError(f"terminal path must be inside the project root: {candidate}")
    return candidate


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
                "system": _is_protected_tmux_session(name),
            }
        )
    sessions.sort(key=lambda item: item["name"])
    return sessions


def _list_live_tmux_sessions() -> List[Dict[str, Any]]:
    sessions = _list_webui_tmux_sessions()
    if not any(session["name"] == WORKFLOW_EXECUTE_SESSION_NAME for session in sessions):
        try:
            if _tmux_session_exists(WORKFLOW_EXECUTE_SESSION_NAME):
                sessions.append(
                    {
                        "name": WORKFLOW_EXECUTE_SESSION_NAME,
                        "attached": False,
                        "created_at": 0,
                        "windows": 1,
                    }
                )
        except RuntimeError:
            pass
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
        if name == WORKFLOW_EXECUTE_SESSION_NAME:
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


def _create_named_tmux_session(session_name: str, start_dir: Path | None = None) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    _run_tmux_command(
        ["new-session", "-d", "-s", safe_name, *(["-c", str(start_dir)] if start_dir is not None else []), "/bin/bash"],
        check=True,
    )
    _initialize_tmux_session_env(safe_name)
    return safe_name


def _send_tmux_command_literal(session_name: str, command: str) -> None:
    safe_name = _validate_tmux_session_name_any(session_name)
    safe_command = _coerce_command(command)
    _run_tmux_command(["set-buffer", "--", safe_command], check=True)
    _run_tmux_command(["paste-buffer", "-t", safe_name], check=True)
    _run_tmux_command(["send-keys", "-t", safe_name, "Enter"], check=True)
    _run_tmux_command(["delete-buffer"], check=False)


def _tmux_session_env_command(session_name: str) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    return f"export TMUX_SESSION_NAME={shlex.quote(safe_name)}"


def _initialize_tmux_session_env(session_name: str) -> None:
    _send_tmux_command_literal(session_name, _tmux_session_env_command(session_name))


def _create_webui_tmux_session(command: str, start_dir: Path | None = None) -> str:
    session_name = f"{TMUX_SESSION_PREFIX}{int(time.time())}-{secrets.token_hex(2)}"
    _run_tmux_command(
        ["new-session", "-d", "-s", session_name, *(["-c", str(start_dir)] if start_dir is not None else []), "/bin/bash"],
        check=True,
    )
    _run_tmux_command(["set-option", "-t", session_name, "remain-on-exit", "on"], check=True)
    _initialize_tmux_session_env(session_name)
    _send_tmux_command_literal(session_name, command)
    return session_name


def _create_native_tmux_session(command: str, start_dir: Path | None = None) -> str:
    session_name = f"{NATIVE_TMUX_SESSION_PREFIX}{int(time.time())}-{secrets.token_hex(2)}"
    _run_tmux_command(
        ["new-session", "-d", "-s", session_name, *(["-c", str(start_dir)] if start_dir is not None else []), "/bin/bash"],
        check=True,
    )
    _run_tmux_command(["set-option", "-t", session_name, "remain-on-exit", "on"], check=True)
    _initialize_tmux_session_env(session_name)
    _send_tmux_command_literal(session_name, command)
    return session_name


def _create_web_shell_tmux_session(start_dir: Path, shell_path: str | None = None) -> str:
    session_name = f"{WEB_SHELL_TMUX_SESSION_PREFIX}{secrets.token_hex(4)}"
    resolved_shell = shell_path or _resolve_system_shell()
    _run_tmux_command(
        ["new-session", "-d", "-s", session_name, "-c", str(start_dir), resolved_shell, "-l"],
        check=True,
    )
    _initialize_tmux_session_env(session_name)
    return session_name


def _create_or_get_web_shell_tmux_session(
    start_dir: Path,
    shell_path: str | None = None,
    session_name: str | None = None,
) -> str:
    resolved_shell = shell_path or _resolve_system_shell()
    if session_name:
        safe_name = _validate_tmux_session_name_any(session_name)
        if _tmux_session_exists(safe_name):
            return safe_name
        _run_tmux_command(
            ["new-session", "-d", "-s", safe_name, "-c", str(start_dir), resolved_shell, "-l"],
            check=True,
        )
        _initialize_tmux_session_env(safe_name)
        return safe_name
    return _create_web_shell_tmux_session(start_dir, shell_path=resolved_shell)


def _kill_tmux_session(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name(session_name)
    proc = _run_tmux_command(["kill-session", "-t", safe_name], check=False)
    if proc.returncode == 0:
        return True
    message = (proc.stderr or proc.stdout or "").lower()
    if "can't find session" in message:
        return False
    raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to kill tmux session")


def _kill_tmux_session_any(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name_any(session_name)
    proc = _run_tmux_command(["kill-session", "-t", safe_name], check=False)
    if proc.returncode == 0:
        return True
    message = (proc.stderr or proc.stdout or "").lower()
    if "can't find session" in message:
        return False
    raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to kill tmux session")


def _is_protected_tmux_session(session_name: str) -> bool:
    return session_name.startswith(PROTECTED_TMUX_SESSION_PREFIXES)


def _tmux_pane_target_any(session_name: str) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    proc = _run_tmux_command(
        ["list-panes", "-t", safe_name, "-F", "#{session_name}:#{window_index}.#{pane_index}"],
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip().lower()
        if "can't find session" in message:
            raise RuntimeError(f"tmux session not found: {safe_name}")
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to resolve tmux pane target")
    pane_target = next((line.strip() for line in (proc.stdout or "").splitlines() if line.strip()), "")
    if not pane_target:
        raise RuntimeError("unable to resolve tmux pane target")
    return pane_target


def _capture_tmux_pane_history_any(session_name: str) -> Dict[str, str]:
    pane_target = _tmux_pane_target_any(session_name)
    proc = _run_tmux_command(
        ["capture-pane", "-pJ", "-S", "-", "-E", "-", "-t", pane_target],
        check=False,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip().lower()
        if "can't find pane" in message or "can't find session" in message:
            raise RuntimeError(f"tmux session not found: {session_name}")
        raise RuntimeError((proc.stderr or proc.stdout or "").strip() or "unable to capture tmux pane history")
    command = f"tmux capture-pane -pJ -S - -E - -t {pane_target}"
    return {
        "session": _validate_tmux_session_name_any(session_name),
        "pane_target": pane_target,
        "command": command,
        "content": proc.stdout or "",
    }


def _is_project_managed_tmux_session(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name_any(session_name)
    return (
        safe_name.startswith(TMUX_SESSION_PREFIX)
        or safe_name.startswith(NATIVE_TMUX_SESSION_PREFIX)
        or safe_name == WORKFLOW_EXECUTE_SESSION_NAME
    )


def _terminal_history_title(saved_at: datetime) -> str:
    return saved_at.strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_saved_terminal_history_id(history_id: str) -> str:
    value = (history_id or "").strip()
    if not value:
        raise ValueError("saved history id is required")
    if not SAVED_TERMINAL_HISTORY_ID_RE.fullmatch(value):
        raise ValueError("invalid saved history id")
    return value


def _saved_terminal_history_path(history_id: str) -> Path:
    safe_id = _safe_saved_terminal_history_id(history_id)
    history_dir = _terminal_histories_dir().resolve()
    candidate = (history_dir / safe_id).resolve()
    if candidate.parent != history_dir:
        raise ValueError("invalid saved history id")
    return candidate


def _session_from_saved_terminal_history_id(history_id: str) -> str:
    safe_id = _safe_saved_terminal_history_id(history_id)
    stem = Path(safe_id).stem
    parts = stem.split("-", 2)
    return parts[2] if len(parts) == 3 else ""


def _save_tmux_pane_history_before_kill(session_name: str) -> Dict[str, Any] | None:
    safe_name = _validate_tmux_session_name_any(session_name)
    if not _is_project_managed_tmux_session(safe_name):
        return None
    try:
        history = _capture_tmux_pane_history_any(safe_name)
        saved_at = datetime.now(timezone.utc)
        history_dir = _terminal_histories_dir()
        history_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{saved_at.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}-{safe_name}.md"
        path = _saved_terminal_history_path(file_name)
        path.write_text(str(history.get("content") or ""), encoding="utf-8")
        return {
            "id": file_name,
            "session": safe_name,
            "title": _terminal_history_title(saved_at),
            "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
            "path": str(path),
        }
    except Exception as exc:
        logger.warning("failed to save tmux history before killing %s: %s", safe_name, exc)
        return None


def _kill_tmux_session_with_history(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name_any(session_name)
    with _TERMINAL_HISTORY_KILL_LOCK:
        _save_tmux_pane_history_before_kill(safe_name)
        return _kill_tmux_session_any(safe_name)


def _saved_terminal_history_entry(path: Path) -> Dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        history_id = _safe_saved_terminal_history_id(path.name)
    except ValueError:
        return None
    try:
        stat = path.stat()
    except OSError:
        return None
    saved_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return {
        "id": history_id,
        "session": _session_from_saved_terminal_history_id(history_id),
        "title": _terminal_history_title(saved_at),
        "saved_at": saved_at.isoformat().replace("+00:00", "Z"),
        "size": stat.st_size,
    }


def _list_saved_terminal_histories() -> List[Dict[str, Any]]:
    history_dir = _terminal_histories_dir()
    if not history_dir.is_dir():
        return []
    entries: List[Dict[str, Any]] = []
    for path in history_dir.iterdir():
        entry = _saved_terminal_history_entry(path)
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda item: (str(item.get("saved_at") or ""), str(item.get("id") or "")), reverse=True)
    return entries


def _read_saved_terminal_history(history_id: str) -> Dict[str, str]:
    safe_id = _safe_saved_terminal_history_id(history_id)
    path = _saved_terminal_history_path(safe_id)
    if not path.is_file():
        raise FileNotFoundError("saved history not found")
    entry = _saved_terminal_history_entry(path)
    if entry is None:
        raise ValueError("invalid saved history id")
    return {
        "id": safe_id,
        "session": str(entry.get("session") or ""),
        "pane_target": str(entry.get("session") or ""),
        "command": f"saved terminal history: {safe_id}",
        "content": path.read_text(encoding="utf-8"),
        "title": str(entry.get("title") or ""),
        "saved_at": str(entry.get("saved_at") or ""),
    }


def _delete_saved_terminal_history(history_id: str) -> bool:
    path = _saved_terminal_history_path(history_id)
    if not path.is_file():
        return False
    path.unlink()
    return True


def _pane_current_command_any(session_name: str) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    proc = _run_tmux_command(["display-message", "-p", "-t", safe_name, "#{pane_current_command}"], check=False)
    if proc.returncode != 0:
        return ""
    pane_command = (proc.stdout or "").strip().lower()
    if pane_command and pane_command not in {"python", "python3", "bash", "sh"}:
        return pane_command
    detected = _detect_agent_bin_for_session_any(safe_name)
    return detected or pane_command


def _known_provider_bins() -> set[str]:
    bins: set[str] = set()
    for provider in load_llm_providers():
        bin_name = str(provider.get("bin") or "").strip().lower()
        if bin_name:
            bins.add(bin_name)
    return bins


def _ps_children_pids(parent_pid: int) -> list[int]:
    if parent_pid <= 1 or shutil.which("pgrep") is None:
        return []
    proc = subprocess.run(
        ["pgrep", "-P", str(parent_pid)],
        capture_output=True,
        text=True,
        check=False,
        env=safe_env(),
    )
    if proc.returncode != 0:
        return []
    child_pids: list[int] = []
    for line in (proc.stdout or "").splitlines():
        raw = line.strip()
        if raw.isdigit():
            child_pids.append(int(raw))
    return child_pids


def _ps_command(pid: int) -> str:
    if pid <= 1:
        return ""
    proc = subprocess.run(
        ["ps", "-p", str(pid), "-o", "comm="],
        capture_output=True,
        text=True,
        check=False,
        env=safe_env(),
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip().lower()


def _detect_agent_bin_for_session_any(session_name: str) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    pane_proc = _run_tmux_command(["display-message", "-p", "-t", safe_name, "#{pane_pid}"], check=False)
    if pane_proc.returncode != 0:
        return ""
    pane_pid_raw = (pane_proc.stdout or "").strip()
    if not pane_pid_raw.isdigit():
        return ""
    known_bins = _known_provider_bins()
    if not known_bins:
        return ""

    queue = _ps_children_pids(int(pane_pid_raw))
    seen = set(queue)
    matches: list[str] = []
    while queue:
        pid = queue.pop(0)
        command = os.path.basename(_ps_command(pid))
        if command in known_bins:
            matches.append(command)
        for child_pid in _ps_children_pids(pid):
            if child_pid not in seen:
                seen.add(child_pid)
                queue.append(child_pid)
    return matches[-1] if matches else ""


def _provider_exit_session_shortcut(provider: Dict[str, Any]) -> str:
    raw = provider.get("exit-session")
    if not isinstance(raw, str) or not raw.strip():
        raw = provider.get("exit_session")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "ctrl+c"


def _send_exit_session_shortcut_any(session_name: str, provider: Dict[str, Any]) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    raw = _provider_exit_session_shortcut(provider)
    steps = [step.strip().lower() for step in raw.splitlines() if step.strip()]
    if not steps:
        steps = ["ctrl+c"]
    time.sleep(1.5)
    for step in steps:
        if step in {"ctrl+c", "^c", "c-c"}:
            _run_tmux_command(["send-keys", "-t", safe_name, "C-c"], check=False)
        elif step in {"enter", "return"}:
            _run_tmux_command(["send-keys", "-t", safe_name, "Enter"], check=False)
        elif step in {"esc", "escape"}:
            _run_tmux_command(["send-keys", "-t", safe_name, "Escape"], check=False)
            time.sleep(1.0)
            continue
        else:
            _run_tmux_command(["send-keys", "-t", safe_name, step, "Enter"], check=False)
        time.sleep(0.35)
    return raw


def _maybe_send_exit_session_shortcut_any(session_name: str, provider: Dict[str, Any]) -> str:
    safe_name = _validate_tmux_session_name_any(session_name)
    provider_id = str(provider.get("id") or "").strip()
    provider_bin = str(provider.get("bin") or "").strip().lower()
    current_command = _pane_current_command_any(safe_name)
    logger.info(
        "[workflow-execute] exit_session_check session=%s provider=%s provider_bin=%s current_command=%s",
        safe_name,
        provider_id,
        provider_bin,
        current_command,
    )
    shortcut = _send_exit_session_shortcut_any(safe_name, provider)
    logger.info(
        "[workflow-execute] exit_session_sent session=%s provider=%s shortcut=%r",
        safe_name,
        provider_id,
        shortcut,
    )
    return shortcut


def _build_provider_command(
    *,
    provider_id: str,
    prompt: str,
    sandbox: Any,
    auto: Any,
    network: Any,
    extra_env: Dict[str, str] | None = None,
) -> tuple[Dict[str, Any], str, str]:
    provider = get_provider(provider_id)
    cmd_list = build_terminal_command(
        provider,
        prompt,
        auto_allow=auto,
        network_allow=network,
        sandbox_mode=sandbox,
    )
    env_overrides: Dict[str, str] = _resolve_provider_env(provider)
    if extra_env:
        env_overrides.update({str(key): str(value) for key, value in extra_env.items()})
    if provider.get("id") == "opencode" and auto:
        opencode_config = str(_REPO_ROOT / "config" / "opencode-yolo.json")
        env_overrides["OPENCODE_CONFIG"] = opencode_config
        display_command = format_command_for_log(cmd_list, env_overrides)
    else:
        display_command = format_command_for_log(cmd_list, env_overrides)

    launch_dir = _REPO_ROOT / ".skillpilot" / "temp" / "tmux-argv"
    launch_dir.mkdir(parents=True, exist_ok=True)
    payload_path = launch_dir / f"{int(time.time())}-{uuid4().hex[:8]}.json"
    payload_path.write_text(
        json.dumps({"argv": cmd_list, "env": env_overrides}, ensure_ascii=False),
        encoding="utf-8",
    )
    launcher = _REPO_ROOT / "core" / "engine" / "exec_argv.py"
    command = shlex.join(["python3", str(launcher), str(payload_path)])
    return provider, command, display_command


def _start_workflow_agent_in_session(
    *,
    session_name: str,
    prompt: str,
    provider_id: str,
    sandbox: Any,
    auto: Any,
    network: Any,
    previous_provider: Dict[str, Any] | None,
    workflow_file: str,
    current_node_id: int,
    run_id: str,
) -> tuple[Dict[str, Any], str]:
    safe_name = _validate_tmux_session_name_any(session_name)
    if previous_provider is not None:
        previous_provider_bin = str(previous_provider.get("bin") or "").strip().lower()
        shortcut = _send_exit_session_shortcut_any(safe_name, previous_provider)
        logger.info(
            "[workflow-execute] session_rotate session=%s previous_provider=%s exit_shortcut=%s",
            safe_name,
            str(previous_provider.get("id") or ""),
            shortcut,
        )
        time.sleep(1.0)
        if previous_provider_bin and _pane_current_command_any(safe_name) == previous_provider_bin:
            _send_exit_session_shortcut_any(safe_name, previous_provider)
            time.sleep(1.0)
        if previous_provider_bin and _pane_current_command_any(safe_name) == previous_provider_bin:
            raise RuntimeError(
                f"Failed to exit current agent session '{previous_provider_bin}' in tmux session '{safe_name}'."
            )
    provider, command, display_command = _build_provider_command(
        provider_id=provider_id,
        prompt=prompt,
        sandbox=sandbox,
        auto=auto,
        network=network,
        extra_env={
            "TMUX_SESSION_NAME": safe_name,
            "SKILL_PILOT_WORKFLOW_NODE": "1",
            "SKILL_PILOT_WORKFLOW_FILE": str(workflow_file),
            "SKILL_PILOT_WORKFLOW_NODE_ID": str(current_node_id),
            "SKILL_PILOT_WORKFLOW_RUN_ID": str(run_id),
        },
    )
    _send_tmux_command_literal(safe_name, command)
    logger.info(
        "[workflow-execute] session_launch session=%s provider=%s command=%s launcher=%s",
        safe_name,
        str(provider.get("id") or ""),
        display_command,
        command,
    )
    return provider, command


def _workflow_execute_status() -> Dict[str, Any]:
    with _WORKFLOW_EXECUTE_LOCK:
        thread = _WORKFLOW_EXECUTE_STATE.get("thread")
        data = {k: v for k, v in _WORKFLOW_EXECUTE_STATE.items() if k != "thread"}
        data["thread_alive"] = bool(thread and thread.is_alive())
        return data


def _set_workflow_execute_state(**updates: Any) -> None:
    with _WORKFLOW_EXECUTE_LOCK:
        _WORKFLOW_EXECUTE_STATE.update(updates)


def _reset_workflow_execute_state(status: str = "idle", error: str = "") -> None:
    with _WORKFLOW_EXECUTE_LOCK:
        _WORKFLOW_EXECUTE_STATE.update(
            {
                "thread": None,
                "token": "",
                "session_name": WORKFLOW_EXECUTE_SESSION_NAME,
                "session_managed": False,
                "status": status,
                "workflow": "",
                "run_id": "",
                "output_root": "",
                "error": error,
                "started_at": 0.0,
                "finished_at": time.time() if status in {"finished", "error", "terminated"} else 0.0,
                "next_node_trigger": "auto_continue",
                "waiting_for_continue": False,
                "current_node_id": 0,
                "current_node_name": "",
                "current_output_file": "",
                "current_provider_id": "",
                "current_provider_bin": "",
                "has_remaining_nodes": False,
            }
        )


def _notify_workflow_tmux_message(session_name: str, message: str) -> None:
    safe_message = str(message or "").strip()
    if not safe_message:
        return
    _send_tmux_command_literal(session_name, f"echo {shlex.quote(safe_message)}")


def _await_workflow_continue_transition(timeout_s: float = 5.0) -> Dict[str, Any]:
    deadline = time.time() + max(0.0, float(timeout_s))
    latest = _workflow_execute_status()
    while time.time() < deadline:
        latest = _workflow_execute_status()
        if not latest.get("thread_alive"):
            return latest
        if not bool(latest.get("waiting_for_continue")):
            return latest
        time.sleep(0.1)
    return _workflow_execute_status()


def request_workflow_continue_signal(source: str = "api") -> Dict[str, Any]:
    status = _workflow_execute_status()
    if not status.get("thread_alive"):
        return {
            "accepted": False,
            "status": status,
            "message": "No active workflow execution thread.",
        }
    if status.get("next_node_trigger") != "start_by_prompt":
        return {
            "accepted": False,
            "status": status,
            "message": "Workflow is not using start-by-prompt mode.",
        }

    session_name = str(status.get("session_name") or WORKFLOW_EXECUTE_SESSION_NAME)
    output_file = str(status.get("current_output_file") or "").strip()
    waiting_for_continue = bool(status.get("waiting_for_continue"))
    has_remaining_nodes = bool(status.get("has_remaining_nodes"))
    if not waiting_for_continue:
        return {
            "accepted": False,
            "status": status,
            "message": "Workflow is not currently waiting for a continue signal.",
        }
    if not has_remaining_nodes:
        return {
            "accepted": False,
            "status": status,
            "message": "No remaining workflow nodes to continue.",
        }

    if not output_file:
        try:
            _notify_workflow_tmux_message(
                session_name,
                "User asked to continue to the next workflow node, but the current node output file is not ready. Please finish the current task first.",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[workflow-execute] continue_notify_failed session=%s error=%s", session_name, exc)
        return {
            "accepted": False,
            "status": _workflow_execute_status(),
            "message": "Current node output file is not ready.",
        }

    if not Path(output_file).exists():
        try:
            _notify_workflow_tmux_message(
                session_name,
                "User asked to continue to the next workflow node, but the current node output file is not ready. Please finish the current task first.",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[workflow-execute] continue_notify_failed session=%s error=%s", session_name, exc)
        return {
            "accepted": False,
            "status": _workflow_execute_status(),
            "message": "Current node output file is not ready.",
        }

    _WORKFLOW_EXECUTE_CONTINUE.set()
    logger.info(
        "[workflow-execute] continue_signal source=%s session=%s output_file=%s waiting_for_continue=%s",
        source,
        session_name,
        output_file,
        waiting_for_continue,
    )
    updated_status = _await_workflow_continue_transition()
    advanced = not bool(updated_status.get("waiting_for_continue"))
    return {
        "accepted": True,
        "status": updated_status,
        "message": "Continue signal accepted and workflow resumed."
        if advanced
        else "Continue signal accepted, but workflow is still waiting to advance.",
    }


def _validate_writable_session_name(session_name: str) -> str:
    value = (session_name or "").strip()
    if value == WORKFLOW_EXECUTE_SESSION_NAME:
        return _validate_tmux_session_name_any(value)
    if _is_protected_tmux_session(value):
        return _validate_tmux_session_name_any(value)
    if value.startswith(WEB_SHELL_TMUX_SESSION_PREFIX):
        return _validate_tmux_session_name_any(value)
    return _validate_tmux_session_name(value)


def _cleanup_webui_tmux_session(session_name: str) -> bool:
    safe_name = _validate_tmux_session_name_any(session_name)
    if not safe_name.startswith(TMUX_SESSION_PREFIX):
        raise ValueError(f"tmux session must start with '{TMUX_SESSION_PREFIX}'")
    return _kill_tmux_session_with_history(safe_name)


def _cleanup_webui_tmux_sessions() -> int:
    removed_count = 0
    for session in _list_webui_tmux_sessions():
        try:
            if _kill_tmux_session_with_history(session["name"]):
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
        try:
            removed = _kill_tmux_session_with_history(name)
        except RuntimeError as exc:
            logger.warning("failed to remove stale native tmux session %s: %s", name, exc)
            continue
        if removed:
            removed_count += 1
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


def _execute_workflow_in_terminal_thread(
    *,
    workflow_file: Path,
    workflow_prompt: str,
    session_name: str,
    run_token: str,
    resume: bool,
    sandbox: Any,
    auto: Any,
    network: Any,
    next_node_trigger: str = "auto_continue",
    external_first_node: bool = False,
    startup_event: threading.Event | None = None,
    startup_result: Dict[str, Any] | None = None,
) -> None:
    started_at = time.time()
    graph = None
    output_root: Path | None = None
    startup_signaled = False

    def thread_is_current() -> bool:
        with _WORKFLOW_EXECUTE_LOCK:
            return _WORKFLOW_EXECUTE_STATE.get("thread") is threading.current_thread()

    def run_is_current() -> bool:
        with _WORKFLOW_EXECUTE_LOCK:
            return (
                _WORKFLOW_EXECUTE_STATE.get("thread") is threading.current_thread()
                and _WORKFLOW_EXECUTE_STATE.get("token") == run_token
            )

    def signal_startup(**values: Any) -> None:
        nonlocal startup_signaled
        if startup_signaled:
            return
        if startup_result is not None:
            startup_result.update(values)
        if startup_event is not None:
            startup_event.set()
        startup_signaled = True

    def wait_for_output_file(output_file: Path, *, node_id: int) -> None:
        wait_started = time.time()
        while True:
            if output_file.exists():
                return
            if not run_is_current():
                raise RuntimeError("workflow execution superseded by a newer run")
            if not _tmux_session_exists(session_name):
                raise RuntimeError(f"workflow tmux session was terminated during node {node_id}")
            if time.time() - wait_started > 3600:
                raise TimeoutError(f"timed out waiting for node output file: {output_file}")
            if _WORKFLOW_EXECUTE_STOP.is_set():
                raise RuntimeError("workflow execution stopped by user")
            _WORKFLOW_EXECUTE_STOP.wait(1.0)

    try:
        graph = load_workflow_graph(workflow_file, WORKFLOWS_DIR)
        instruction_file_path = parse_instruction_file_path(workflow_prompt)
        reference_file_paths = parse_reference_file_paths(workflow_prompt)
        if instruction_file_path:
            workflow_project_path = f"core/workflows/{graph.workflow_relative_path}"
            task_run_id, _ = workflow_task_output_dir(
                _terminal_workflow_base_dir(),
                instruction_file_path,
                workflow_project_path,
                repo_root=_REPO_ROOT,
                reference_file_paths=reference_file_paths,
            )
            run_id, output_root = create_run_output_dir(
                _terminal_workflow_base_dir(),
                run_id=task_run_id,
                cleanup_output_dir=not resume,
            )
        else:
            run_id, output_root = create_run_output_dir(
                _terminal_workflow_base_dir(),
                cleanup_base_dir=True,
            )
        task_workspace = parse_task_workspace(workflow_prompt)
        if run_is_current():
            _set_workflow_execute_state(
                status="running",
                workflow=graph.workflow_relative_path,
                run_id=run_id,
                output_root=str(output_root),
                error="",
                started_at=started_at,
                finished_at=0.0,
                next_node_trigger=next_node_trigger,
                waiting_for_continue=False,
                current_node_id=0,
                current_node_name="",
                current_output_file="",
                current_provider_id="",
                current_provider_bin="",
                has_remaining_nodes=False,
            )
        logger.info(
            "[workflow-execute] thread_start workflow=%s workflow_name=%s session=%s run_id=%s output_root=%s",
            graph.workflow_relative_path,
            graph.workflow_name,
            session_name,
            run_id,
            output_root,
        )

        node_status: Dict[int, str] = {node_id: "pending" for node_id in graph.upstream_agents}
        pending_upstream_count: Dict[int, int] = {
            node_id: len(up_ids) for node_id, up_ids in graph.upstream_agents.items()
        }
        has_failed_upstream: Dict[int, bool] = {node_id: False for node_id in graph.upstream_agents}
        ready: List[int] = [node_id for node_id, count in pending_upstream_count.items() if count == 0]
        previous_provider: Dict[str, Any] | None = None
        external_first_node_pending = bool(external_first_node)

        while ready:
            if not run_is_current():
                raise RuntimeError("workflow execution superseded by a newer run")
            if _WORKFLOW_EXECUTE_STOP.is_set():
                raise RuntimeError("workflow execution stopped by user")
            if not _tmux_session_exists(session_name):
                raise RuntimeError(f"workflow tmux session was terminated: {session_name}")
            ready.sort()
            node_id = ready.pop(0)
            if has_failed_upstream.get(node_id):
                node_status[node_id] = "blocked"
                continue

            node = graph.id_to_node[node_id]
            data = node.get("data") if isinstance(node.get("data"), dict) else {}
            provider_id = str(data.get("provider_id") or "").strip()
            upstream_node_ids = list(graph.upstream_agents[node_id])
            output_file = node_output_path(output_root, node_id, node_name(node))
            if resume and output_file.exists():
                logger.info(
                    "[workflow-execute] node_resume_skip node_id=%s node_name=%s output_file=%s",
                    node_id,
                    node_name(node),
                    output_file,
                )
                node_status[node_id] = "done"
                for downstream_id in graph.downstream_agents.get(node_id, []):
                    pending_upstream_count[downstream_id] = max(0, pending_upstream_count[downstream_id] - 1)
                    if pending_upstream_count[downstream_id] == 0:
                        if has_failed_upstream[downstream_id]:
                            node_status[downstream_id] = "blocked"
                        else:
                            ready.append(downstream_id)
                continue
            prompt = build_node_prompt(
                graph=graph,
                current_node=node,
                workflow_prompt=workflow_prompt,
                output_root=output_root,
                upstream_node_ids=upstream_node_ids,
                task_workspace=task_workspace,
                start_by_prompt_mode=(next_node_trigger == "start_by_prompt"),
            )
            if output_file.exists():
                try:
                    output_file.unlink()
                except OSError:
                    pass

            node_status[node_id] = "running"
            if run_is_current():
                _set_workflow_execute_state(
                    status="running",
                    waiting_for_continue=False,
                    current_node_id=node_id,
                    current_node_name=node_name(node),
                    current_output_file=str(output_file),
                    current_provider_id=provider_id,
                    has_remaining_nodes=False,
                )
            logger.info(
                "[workflow-execute] node_start node_id=%s node_name=%s provider_id=%s upstream_ids=%s output_file=%s",
                node_id,
                node_name(node),
                provider_id,
                upstream_node_ids,
                output_file,
            )
            logger.info("[workflow-execute] node_prompt node_id=%s\n%s", node_id, prompt)
            try:
                if external_first_node_pending:
                    previous_provider = _active_session_provider(session_name)
                    if previous_provider is not None and run_is_current():
                        _set_workflow_execute_state(
                            current_provider_id=str(previous_provider.get("id") or ""),
                            current_provider_bin=str(previous_provider.get("bin") or ""),
                        )
                    signal_startup(
                        status="ok",
                        prompt=prompt,
                        workflow=graph.workflow_relative_path,
                        workflow_name=graph.workflow_name,
                        run_id=run_id,
                        output_root=str(output_root),
                        node_id=node_id,
                        node_name=node_name(node),
                        output_file=str(output_file),
                        next_node_trigger=next_node_trigger,
                        session_name=session_name,
                    )
                    external_first_node_pending = False
                    wait_for_output_file(output_file, node_id=node_id)
                else:
                    previous_provider, _ = _start_workflow_agent_in_session(
                        session_name=session_name,
                        prompt=prompt,
                        provider_id=provider_id,
                        sandbox=sandbox,
                        auto=auto,
                        network=network,
                        previous_provider=previous_provider,
                        workflow_file=f"core/workflows/{graph.workflow_relative_path}",
                        current_node_id=node_id,
                        run_id=run_id,
                    )
                    if run_is_current():
                        _set_workflow_execute_state(
                            current_provider_id=str(previous_provider.get("id") or ""),
                            current_provider_bin=str(previous_provider.get("bin") or ""),
                        )

                    wait_for_output_file(output_file, node_id=node_id)

                output_text = output_file.read_text(encoding="utf-8", errors="replace")
                logger.info("[workflow-execute] node_output node_id=%s output_file=%s\n%s", node_id, output_file, output_text)
                node_status[node_id] = "done"
            except (RuntimeError, TimeoutError):
                raise  # session killed or timeout — abort workflow
            except Exception as exc:  # noqa: BLE001
                node_status[node_id] = "failed"
                logger.error("[workflow-execute] node_failed node_id=%s error=%s", node_id, exc)
                for downstream_id in graph.downstream_agents.get(node_id, []):
                    has_failed_upstream[downstream_id] = True

            for downstream_id in graph.downstream_agents.get(node_id, []):
                pending_upstream_count[downstream_id] = max(0, pending_upstream_count[downstream_id] - 1)
                if node_status[node_id] != "done":
                    has_failed_upstream[downstream_id] = True
                if pending_upstream_count[downstream_id] == 0:
                    if has_failed_upstream[downstream_id]:
                        node_status[downstream_id] = "blocked"
                    else:
                        ready.append(downstream_id)

            has_remaining_nodes = len(ready) > 0
            if node_status[node_id] == "done" and next_node_trigger == "start_by_prompt":
                if has_remaining_nodes:
                    if run_is_current():
                        _set_workflow_execute_state(
                            status="waiting_for_continue",
                            waiting_for_continue=True,
                            current_node_id=node_id,
                            current_node_name=node_name(node),
                            current_output_file=str(output_file),
                            has_remaining_nodes=has_remaining_nodes,
                        )
                    while True:
                        if not run_is_current():
                            raise RuntimeError("workflow execution superseded by a newer run")
                        if _WORKFLOW_EXECUTE_STOP.is_set():
                            raise RuntimeError("workflow execution stopped by user")
                        if not _tmux_session_exists(session_name):
                            raise RuntimeError(f"workflow tmux session was terminated during node {node_id}")
                        if _WORKFLOW_EXECUTE_CONTINUE.wait(1.0):
                            _WORKFLOW_EXECUTE_CONTINUE.clear()
                            break

                    if run_is_current():
                        _set_workflow_execute_state(status="running", waiting_for_continue=False)
                else:
                    if previous_provider is not None:
                        _maybe_send_exit_session_shortcut_any(session_name, previous_provider)
                        previous_provider = None
                    _send_tmux_command_literal(session_name, "echo 'The workflow has completed.'")
                    if run_is_current():
                        _set_workflow_execute_state(
                            status="running",
                            waiting_for_continue=False,
                            has_remaining_nodes=False,
                        )
        if external_first_node_pending:
            signal_startup(
                status="ok",
                prompt="Workflow already complete. No pending workflow node requires execution.",
                workflow=graph.workflow_relative_path if graph is not None else "",
                workflow_name=str(graph.workflow_name) if graph is not None else "",
                run_id=run_id,
                output_root=str(output_root),
                node_id=0,
                node_name="",
                output_file="",
                next_node_trigger=next_node_trigger,
                session_name=session_name,
            )

        failed_nodes = [node_id for node_id, status in node_status.items() if status != "done"]
        if failed_nodes:
            raise RuntimeError(f"workflow finished with incomplete nodes: {failed_nodes}")

        finished_at = time.time()
        if run_is_current():
            _set_workflow_execute_state(
                status="finished",
                finished_at=finished_at,
                waiting_for_continue=False,
                current_node_id=0,
                current_node_name="",
                current_output_file="",
                current_provider_id="",
                current_provider_bin="",
                has_remaining_nodes=False,
            )
        logger.info(
            "[workflow-execute] thread_finish workflow=%s session=%s run_id=%s duration_sec=%.3f",
            graph.workflow_relative_path,
            session_name,
            run_id,
            finished_at - started_at,
        )
    except Exception as exc:  # noqa: BLE001
        finished_at = time.time()
        if run_is_current():
            _set_workflow_execute_state(
                status="error",
                error=str(exc),
                finished_at=finished_at,
                waiting_for_continue=False,
            )
            logger.exception("[workflow-execute] thread_error session=%s error=%s", session_name, exc)
        if external_first_node and not startup_signaled:
            signal_startup(error=str(exc))
    finally:
        if external_first_node and not startup_signaled:
            signal_startup(error="workflow startup did not finish")
        with _WORKFLOW_EXECUTE_LOCK:
            if (
                _WORKFLOW_EXECUTE_STATE.get("thread") is threading.current_thread()
                and _WORKFLOW_EXECUTE_STATE.get("token") == run_token
            ):
                _WORKFLOW_EXECUTE_STATE["thread"] = None


def _start_workflow_execute_thread(
    *,
    workflow_file: Path,
    workflow_prompt: str,
    session_name: str,
    resume: bool,
    sandbox: Any,
    auto: Any,
    network: Any,
    next_node_trigger: str,
    session_managed: bool,
    external_first_node: bool = False,
) -> Dict[str, Any]:
    _WORKFLOW_EXECUTE_STOP.clear()
    _WORKFLOW_EXECUTE_CONTINUE.clear()
    run_token = uuid4().hex
    startup_event = threading.Event() if external_first_node else None
    startup_result: Dict[str, Any] | None = {} if external_first_node else None
    thread = threading.Thread(
        target=_execute_workflow_in_terminal_thread,
        kwargs={
            "workflow_file": workflow_file,
            "workflow_prompt": workflow_prompt,
            "session_name": session_name,
            "run_token": run_token,
            "resume": resume,
            "sandbox": sandbox,
            "auto": auto,
            "network": network,
            "next_node_trigger": next_node_trigger,
            "external_first_node": external_first_node,
            "startup_event": startup_event,
            "startup_result": startup_result,
        },
        daemon=True,
        name="workflow-execute",
    )
    with _WORKFLOW_EXECUTE_LOCK:
        _WORKFLOW_EXECUTE_STATE.update(
            {
                "thread": thread,
                "token": run_token,
                "status": "starting",
                "session_name": session_name,
                "session_managed": bool(session_managed),
                "workflow": str(workflow_file),
                "run_id": "",
                "output_root": "",
                "error": "",
                "started_at": time.time(),
                "finished_at": 0.0,
                "next_node_trigger": next_node_trigger,
                "waiting_for_continue": False,
                "current_node_id": 0,
                "current_node_name": "",
                "current_output_file": "",
                "current_provider_id": "",
                "current_provider_bin": "",
                "has_remaining_nodes": False,
            }
        )
    thread.start()
    result: Dict[str, Any] = {
        "workflow_thread": _workflow_execute_status(),
    }
    if startup_event is not None and startup_result is not None:
        if not startup_event.wait(timeout=5.0):
            _WORKFLOW_EXECUTE_STOP.set()
            _WORKFLOW_EXECUTE_CONTINUE.set()
            raise RuntimeError("workflow monitor startup timed out")
        if startup_result.get("error"):
            raise RuntimeError(str(startup_result["error"]))
        result["startup"] = dict(startup_result)
    return result


def _stop_existing_workflow_execute_thread() -> None:
    status = _workflow_execute_status()
    thread = None
    session_name = str(status.get("session_name") or WORKFLOW_EXECUTE_SESSION_NAME)
    session_managed = bool(status.get("session_managed"))
    with _WORKFLOW_EXECUTE_LOCK:
        thread = _WORKFLOW_EXECUTE_STATE.get("thread")
    if thread and thread.is_alive():
        logger.info("[workflow-execute] stopping_existing_thread status=%s", status.get("status"))
    _WORKFLOW_EXECUTE_STOP.set()
    _WORKFLOW_EXECUTE_CONTINUE.set()
    if session_managed and session_name:
        try:
            _kill_tmux_session_any(session_name)
        except RuntimeError as exc:
            logger.warning("[workflow-execute] failed_to_kill_existing_session session=%s error=%s", session_name, exc)
    if thread and thread.is_alive():
        thread.join(timeout=5.0)
    _reset_workflow_execute_state(status="terminated")
    _WORKFLOW_EXECUTE_CONTINUE.clear()


def cleanup_stale_workflow_session() -> None:
    """Kill any leftover sp-workflow-execute tmux session on engine startup."""
    try:
        if _tmux_session_exists(WORKFLOW_EXECUTE_SESSION_NAME):
            _kill_tmux_session_any(WORKFLOW_EXECUTE_SESSION_NAME)
            logger.info("[workflow-execute] cleanup_stale_session session=%s", WORKFLOW_EXECUTE_SESSION_NAME)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[workflow-execute] cleanup_stale_session_failed session=%s error=%s", WORKFLOW_EXECUTE_SESSION_NAME, exc)
    _reset_workflow_execute_state(status="idle")
    _WORKFLOW_EXECUTE_CONTINUE.clear()


def _is_text_bytes(data: bytes) -> bool:
    return b"\x00" not in data


def _task_type_from_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")):
        return "image"
    if lower.endswith((".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac")):
        return "audio"
    if lower.endswith((".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv")):
        return "video"
    if lower.endswith((".md", ".markdown")):
        return "markdown"
    if lower.endswith((".html", ".htm")):
        return "html"
    return "text"


__all__ = [name for name in globals() if not name.startswith("__")]
