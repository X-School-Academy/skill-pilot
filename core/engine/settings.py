import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent.parent
CONFIG_ENV_PATH = PROJECT_DIR / "config" / ".env"
_SETTINGS_PATH = PROJECT_DIR / "config" / "settings.json5"


def _read_service_setting(*keys: str, default: str = "") -> str:
    """Read a nested value from config/settings.json5.

    Example: _read_service_setting("services", "live_avatar", "server_url")
    Priority: env var overrides are checked by the caller before this helper.
    """
    try:
        import json5 as _json5  # available via engine pyproject.toml dependency

        data = _json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        val: object = data
        for key in keys:
            if not isinstance(val, dict):
                return default
            val = val.get(key)
            if val is None:
                return default
        return str(val) if val is not None else default
    except Exception:
        return default


def _sanitize_single_line_secret(value: str) -> str:
    return re.sub(r"[\r\n]+", "", value).strip()


def _env_or_config(name: str, default: str = "") -> str:
    env_val = _sanitize_single_line_secret(os.getenv(name, ""))
    if env_val:
        return env_val
    return default


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_engine_ws_url() -> str:
    """Return the engine's own WebSocket base URL, e.g. ws://127.0.0.1:3001.

    Reads services.engine.host/port from settings.json5 so the browser
    never has to guess the engine address.
    """
    host = _read_service_setting("services", "engine", "host", default="127.0.0.1")
    port = _read_service_setting("services", "engine", "port", default="3001")
    return f"ws://{host}:{port}"


def get_live_avatar_server_url() -> str:
    # Priority: env var → settings.json5 → hardcoded default
    env_val = _env_or_config("LIVE_AVATAR_SERVER_URL", "")
    if env_val:
        return env_val
    return _read_service_setting("services", "live_avatar", "server_url", default="ws://127.0.0.1:8008")


def get_turn_server_urls() -> str:
    return _env_or_config("TURN_SERVER_URLS", _read_service_setting("turn", "urls"))


def get_turn_server_username() -> str:
    return _env_or_config("TURN_SERVER_USERNAME", _read_service_setting("turn", "username"))


def get_turn_server_password() -> str:
    return _env_or_config("TURN_SERVER_PASSWORD", _read_service_setting("turn", "password"))


def get_discord_bot_token() -> str:
    return _env_or_config("DISCORD_BOT_TOKEN", "")


def get_auth_token() -> str:
    return _env_or_config("AUTH_TOKEN", "")


def get_only_allow_https() -> bool:
    return _is_truthy(_env_or_config("ONLY_ALLOW_HTTPS", "0"))


def ensure_auth_token() -> str:
    token = get_auth_token()
    if token:
        return token
    sys.exit(
        "FATAL: AUTH_TOKEN is not set in config/.env.\n"
        "Add or update it before starting the engine:\n"
        "  core/bin/keys-safe-guard put_key_values AUTH_TOKEN=<your-secret-token>\n"
        "or edit config/.env directly and add:\n"
        "  AUTH_TOKEN=<your-secret-token>"
    )

COURSES_DIR = Path(os.getenv("COURSES_DIR", PROJECT_DIR / "workspace" / "learning")).resolve()
TASKS_DIR = Path(os.getenv("TASKS_DIR", PROJECT_DIR / "workspace" / "tasks")).resolve()
VIBE_CODING_DIR = Path(os.getenv("VIBE_CODING_DIR", PROJECT_DIR / "workspace" / "vibe-coding")).resolve()
RESEARCH_DIR = Path(os.getenv("RESEARCH_DIR", PROJECT_DIR / "workspace" / "research")).resolve()
WORKFLOWS_DIR = Path(os.getenv("WORKFLOWS_DIR", PROJECT_DIR / "core" / "workflows")).resolve()
LLM_PROVIDERS_FILE = Path(
    os.getenv("LLM_PROVIDERS_FILE", PROJECT_DIR / "config" / "ai_providers.json5")
).resolve()
LOCAL_DEV_TOKEN = os.getenv("LOCAL_DEV_TOKEN", str(uuid.uuid4()))
LOCAL_CHROME_TOKEN = os.getenv("LOCAL_CHROME_TOKEN", str(uuid.uuid4()))
TERMINAL_AUTO_IMAGE_URL_PREVIEW = os.getenv("TERMINAL_AUTO_IMAGE_URL_PREVIEW", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Discord bot settings
DISCORD_BOT_TOKEN = get_discord_bot_token()
AUTH_TOKEN = ensure_auth_token()
DISCORD_SESSIONS_DIR = Path(
    os.getenv("DISCORD_SESSIONS_DIR", PROJECT_DIR / ".skillpilot" / "discord" / "sessions")
).resolve()
DISCORD_MAX_BUFFER_TOKENS = int(os.getenv("DISCORD_MAX_BUFFER_TOKENS", "16384"))
DISCORD_BUFFER_MSG_COUNT = int(os.getenv("DISCORD_BUFFER_MSG_COUNT", "20"))
DEFAULT_TTS_PROVIDER = (os.getenv("DEFAULT_TTS_PROVIDER") or "").strip() or None
DEFAULT_IMAGE_PROVIDER = (os.getenv("DEFAULT_IMAGE_PROVIDER") or "").strip() or None

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%d/%b/%Y:%H:%M:%S %z",
)
logging.Formatter.converter = time.localtime
logger = logging.getLogger("webui")
