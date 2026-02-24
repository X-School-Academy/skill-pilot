import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import json5
from llm_service import llm_stream, load_llm_providers, stop_client


@dataclass
class AgentRun:
    id: str
    stage_id: str
    prompt: str
    agent_id: str
    status: str
    client_id: str
    events: List[Dict[str, str]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_STATE_LOCK = threading.Lock()
_ACTIVE_RUN: Optional[AgentRun] = None
_RUN_COUNTER = 0
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SETTINGS_PATH = _REPO_ROOT / "config" / "settings.json5"
_DEFAULT_AGENT_SECURITY: Dict[str, bool] = {"sandbox": True, "auto": True, "network": True}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _push_event(run: AgentRun, category: str, message: str) -> None:
    with run.lock:
        run.events.append(
            {
                "timestamp": _iso_now(),
                "category": category,
                "message": message,
            }
        )


def _provider_exists(provider_id: str) -> bool:
    for provider in load_llm_providers():
        if str(provider.get("id")) == provider_id:
            return True
    return False


def _coerce_bool(value: Any, default: bool) -> bool:
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


def _read_agent_security(provider_id: str) -> Dict[str, bool]:
    flags = dict(_DEFAULT_AGENT_SECURITY)
    try:
        if not _SETTINGS_PATH.is_file():
            return flags
        data = json5.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return flags
        security = data.get("security")
        if not isinstance(security, dict):
            return flags

        # Dev Swarm section is the primary source for this flow.
        dev_swarm = security.get("devSwarm")
        if isinstance(dev_swarm, dict):
            for key in ("sandbox", "auto", "network"):
                flags[key] = _coerce_bool(dev_swarm.get(key), flags[key])

        # Backward-compatible provider-specific override support.
        skill_agent = security.get("skillAgent", dict(_DEFAULT_AGENT_SECURITY))
        if isinstance(skill_agent, dict):
            # Backward-compatible flat defaults under security.skillAgent.
            for key in ("sandbox", "auto", "network"):
                if key in skill_agent:
                    flags[key] = _coerce_bool(skill_agent.get(key), flags[key])

            provider_flags = skill_agent.get(provider_id)
            if isinstance(provider_flags, dict):
                for key in ("sandbox", "auto", "network"):
                    flags[key] = _coerce_bool(provider_flags.get(key), flags[key])

        # Typo-compatible alias support.
        kill_agent = security.get("killAgent")
        if isinstance(kill_agent, dict):
            provider_flags = kill_agent.get(provider_id)
            if isinstance(provider_flags, dict):
                for key in ("sandbox", "auto", "network"):
                    flags[key] = _coerce_bool(provider_flags.get(key), flags[key])
    except Exception:
        return dict(_DEFAULT_AGENT_SECURITY)

    return flags


def get_agents() -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for provider in load_llm_providers():
        provider_id = str(provider.get("id") or "").strip()
        if not provider_id:
            continue
        result.append(
            {
                "id": provider_id,
                "name": str(provider.get("name") or provider_id),
            }
        )
    return result


def get_active_run() -> Optional[AgentRun]:
    return _ACTIVE_RUN


def is_run_active() -> bool:
    run = _ACTIVE_RUN
    return run is not None and run.status == "running"


def _run_worker(run: AgentRun) -> None:
    had_error = False
    pending = ""
    security_flags = _read_agent_security(run.agent_id)
    try:
        for chunk in llm_stream(
            run.prompt,
            run.agent_id,
            run.client_id,
            auto_allow=security_flags["auto"],
            network_allow=security_flags["network"],
            sandbox_mode=security_flags["sandbox"],
        ):
            text = chunk.decode("utf-8", errors="replace")
            if not text:
                continue
            if text == "[-DONE-]":
                continue
            if text == "[-ERROR-]":
                had_error = True
                _push_event(run, "stderr", "Agent process returned an error.")
                continue

            pending += text
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                line = line.rstrip("\r")
                if line:
                    _push_event(run, "output", line)

        if pending.strip():
            _push_event(run, "output", pending.strip())
    except Exception as exc:
        had_error = True
        _push_event(run, "stderr", f"Process error: {exc}")
    finally:
        with _STATE_LOCK:
            if run.status == "running":
                run.status = "failed" if had_error else "succeeded"
        _push_event(run, "status", run.status)


def start_run(stage_id: str, prompt: str, agent_id: str) -> AgentRun:
    global _ACTIVE_RUN, _RUN_COUNTER

    if not _provider_exists(agent_id):
        raise ValueError(f"Unknown agent: {agent_id}")

    with _STATE_LOCK:
        if _ACTIVE_RUN is not None and _ACTIVE_RUN.status == "running":
            raise RuntimeError("A run is already active")
        _RUN_COUNTER += 1
        run_id = f"run-{_RUN_COUNTER}-{int(time.time() * 1000)}"
        run = AgentRun(
            id=run_id,
            stage_id=stage_id,
            prompt=prompt,
            agent_id=agent_id,
            status="running",
            client_id=f"dev-swarm-{run_id}",
        )
        _ACTIVE_RUN = run

    _push_event(run, "system", f"Starting {agent_id} agent...")
    _push_event(run, "system", f"Prompt: {prompt[:300]}")
    _push_event(run, "status", "running")

    thread = threading.Thread(target=_run_worker, args=(run,), daemon=True)
    thread.start()
    return run


def interrupt_run() -> AgentRun:
    run = _ACTIVE_RUN
    if run is None:
        raise RuntimeError("No active run")
    if run.status != "running":
        raise RuntimeError("Run is not active")

    stop_client(run.client_id)
    with _STATE_LOCK:
        run.status = "stopped"
    _push_event(run, "system", "Run interrupted by user")
    _push_event(run, "status", "stopped")
    return run


def get_run_events(run_id: str) -> List[Dict[str, str]]:
    run = _ACTIVE_RUN
    if run is None or run.id != run_id:
        return []
    with run.lock:
        return list(run.events)


def is_run_finished(run_id: str) -> bool:
    run = _ACTIVE_RUN
    if run is None or run.id != run_id:
        return True
    return run.status != "running"
