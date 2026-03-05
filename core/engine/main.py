import logging
import multiprocessing
import os
import signal
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_ENV_PATH = PROJECT_DIR / "config" / ".env"
ENGINE_DIR = Path(__file__).resolve().parent

# In --reload mode, uvicorn has a long-lived parent reloader process that spawns
# child server processes. Load env once in that parent so children inherit env
# without re-reading protected .env every restart.
_ENV_LOADED_FLAG = "SKILL_PILOT_ENV_ALREADY_LOADED"
_ENGINE_CONTROL_PID_ENV = "SKILL_PILOT_ENGINE_CONTROL_PID"
_RELOAD_SIGNAL = signal.SIGUSR1
_RESTART_SIGNAL = signal.SIGUSR2

if multiprocessing.parent_process() is None and os.getenv(_ENV_LOADED_FLAG) != "1":
    from safe_dotenv import load_env_with_safeguard

    load_env_with_safeguard(CONFIG_ENV_PATH, override=False)
    os.environ[_ENV_LOADED_FLAG] = "1"


class _HeartbeatFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        noisy_paths = (
            "/api/heartbeat",
            "/api/terminal/tmux/external-sessions",
        )
        if any(path in msg for path in noisy_paths):
            return False
        return True


# Install filter on uvicorn.access before anything else runs.
logging.getLogger("uvicorn.access").addFilter(_HeartbeatFilter())


def build_app():
    from app_factory import create_app

    return create_app()


def _restart_from_memory() -> None:
    # Do not re-read .env. Restart process with current in-memory environment.
    os.environ[_ENV_LOADED_FLAG] = "1"
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _on_reload_signal(signum, frame):  # type: ignore[no-untyped-def]
    _ = signum
    _ = frame
    from safe_dotenv import load_env_with_safeguard

    loaded = load_env_with_safeguard(CONFIG_ENV_PATH, override=True, require_gui_auth=True)
    if not loaded:
        logging.getLogger("uvicorn.error").error(
            "engine-reload aborted: GUI-authenticated .env read failed or was cancelled"
        )
        return
    _restart_from_memory()


def _on_restart_signal(signum, frame):  # type: ignore[no-untyped-def]
    _ = signum
    _ = frame
    _restart_from_memory()


def _read_engine_service_defaults() -> tuple[str, int]:
    """Read engine host/port from config/settings.json5 services.engine section."""
    try:
        import json5

        settings_path = PROJECT_DIR / "config" / "settings.json5"
        data = json5.loads(settings_path.read_text(encoding="utf-8"))
        engine = data.get("services", {}).get("engine", {})
        host = str(engine.get("host", "127.0.0.1"))
        port = int(engine.get("port", 3001))
        return host, port
    except Exception:
        return "127.0.0.1", 3001


if __name__ == "__main__":
    import argparse
    import uvicorn

    if not os.getenv(_ENGINE_CONTROL_PID_ENV):
        # In --reload mode, parent sets this once; children inherit parent PID target.
        os.environ[_ENGINE_CONTROL_PID_ENV] = str(os.getpid())

    signal.signal(_RELOAD_SIGNAL, _on_reload_signal)
    signal.signal(_RESTART_SIGNAL, _on_restart_signal)

    _default_host, _default_port = _read_engine_service_defaults()

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=_default_host)
    parser.add_argument("--port", type=int, default=_default_port)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on source changes")
    parser.add_argument(
        "--reload-dir",
        action="append",
        dest="reload_dirs",
        help="Directory to watch for reload; can be passed multiple times",
    )
    args = parser.parse_args()

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "format": "[%(asctime)s] %(levelprefix)s %(message)s",
                "datefmt": "%d/%b/%Y:%H:%M:%S %z",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "format": "[%(asctime)s] %(levelprefix)s %(request_line)s %(status_code)s",
                "datefmt": "%d/%b/%Y:%H:%M:%S %z",
            },
        },
        "handlers": {
            "default": {"formatter": "default", "class": "logging.StreamHandler", "stream": "ext://sys.stdout"},
            "access": {"formatter": "access", "class": "logging.StreamHandler", "stream": "ext://sys.stdout"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }

    app_target = "main:build_app"

    uvicorn.run(
        app_target,
        host=args.host,
        port=args.port,
        log_config=log_config,
        factory=True,
        reload=args.reload,
        reload_dirs=args.reload_dirs,
        app_dir=str(ENGINE_DIR) if args.reload else None,
    )
