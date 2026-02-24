import json
import json5
import os
import secrets
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from llm_service import build_terminal_command, get_default_llm_provider_id, get_provider
from settings import logger

_REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEDULE_CONFIG_PATH = _REPO_ROOT / "config" / "schedule.json5"

_scheduler: Optional[AsyncIOScheduler] = None


def load_schedules() -> List[Dict[str, Any]]:
    if not SCHEDULE_CONFIG_PATH.is_file():
        return []
    try:
        data = json5.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("Failed to load schedule config: %s", exc)
    return []


def save_schedules(schedules: List[Dict[str, Any]]) -> None:
    SCHEDULE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    import json
    SCHEDULE_CONFIG_PATH.write_text(
        json.dumps(schedules, indent=2) + "\n", encoding="utf-8"
    )


_PROFILE_PATH = _REPO_ROOT / "config" / "profile.json5"
_SETTINGS_PATH = _REPO_ROOT / "config" / "settings.json5"


def _load_profile_timezone() -> Optional[str]:
    if _PROFILE_PATH.is_file():
        try:
            data = json5.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
            tz_str = data.get("timezone", "")
            if tz_str:
                pytz.timezone(tz_str)  # validate
                return tz_str
        except Exception:
            pass
    # Fall back to local machine timezone
    tz_env = os.environ.get("TZ", "")
    if tz_env:
        try:
            pytz.timezone(tz_env)
            return tz_env
        except Exception:
            pass
    localtime = Path("/etc/localtime")
    if localtime.is_symlink():
        target = str(localtime.resolve())
        if "/zoneinfo/" in target:
            tz_name = target.split("/zoneinfo/", 1)[1]
            try:
                pytz.timezone(tz_name)
                return tz_name
            except Exception:
                pass
    return None

_DEFAULT_SCHEDULE_SECURITY = {"sandbox": True, "auto": True, "network": True}


def _load_schedule_security() -> Dict[str, Any]:
    if not _SETTINGS_PATH.is_file():
        return dict(_DEFAULT_SCHEDULE_SECURITY)
    try:
        data = json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        sec = data.get("security", {}).get("schedules", {})
        result = dict(_DEFAULT_SCHEDULE_SECURITY)
        result.update(sec)
        return result
    except Exception as exc:
        logger.warning("[scheduler] failed to load security settings: %s", exc)
        return dict(_DEFAULT_SCHEDULE_SECURITY)


def _run_scheduled_skill(skill: str, provider_id: str) -> None:
    from routes import _create_webui_tmux_session

    user_tz = _load_profile_timezone()
    if user_tz:
        tz_obj = pytz.timezone(user_tz)
        now = datetime.now(tz_obj)
    else:
        now = datetime.now(timezone.utc).astimezone()
    tz_name = user_tz or now.strftime("%Z") or "UTC"
    iso_time = now.isoformat()

    prompt = (
        f"Use agent skill: {skill} to perform the scheduled task as defined in the skill. "
        f"Current date and time: {iso_time}, timezone: {tz_name}."
    )

    sec = _load_schedule_security()
    provider = get_provider(provider_id or None)
    cmd_list = build_terminal_command(
        provider,
        prompt,
        auto_allow=sec.get("auto", True),
        network_allow=sec.get("network", True),
        sandbox_mode=sec.get("sandbox", True),
    )

    if provider.get("id") == "opencode" and sec.get("auto", True):
        opencode_config = str(_REPO_ROOT / "config" / "opencode-yolo.json")
        command = f"OPENCODE_CONFIG={shlex.quote(opencode_config)} {shlex.join(cmd_list)}"
    else:
        command = shlex.join(cmd_list)

    session_name = _create_webui_tmux_session(command)
    logger.info("[scheduler] created tmux session %s for skill=%s provider=%s", session_name, skill, provider.get("id"))


def start_scheduler(schedules: List[Dict[str, Any]]) -> None:
    global _scheduler
    stop_scheduler()

    user_tz = _load_profile_timezone()
    tz_obj = pytz.timezone(user_tz) if user_tz else None
    logger.info("[scheduler] using timezone: %s", user_tz or "system default")

    _scheduler = AsyncIOScheduler()
    added = 0
    for entry in schedules:
        if not entry.get("enabled", True):
            continue
        cron_str = entry.get("cron", "")
        skill = entry.get("skill", "")
        if not cron_str or not skill:
            continue
        try:
            trigger = CronTrigger.from_crontab(cron_str, timezone=tz_obj)
        except (ValueError, KeyError) as exc:
            logger.warning("[scheduler] invalid cron %r for schedule %s: %s", cron_str, entry.get("id"), exc)
            continue
        provider = entry.get("provider") or get_default_llm_provider_id()
        _scheduler.add_job(
            _run_scheduled_skill,
            trigger=trigger,
            args=[skill, provider],
            id=entry.get("id", secrets.token_hex(4)),
            name=entry.get("name", skill),
            replace_existing=True,
        )
        added += 1

    _scheduler.start()
    logger.info("[scheduler] started with %d jobs", added)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None


def reload_scheduler() -> None:
    schedules = load_schedules()
    start_scheduler(schedules)
