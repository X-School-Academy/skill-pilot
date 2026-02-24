from __future__ import annotations

from threading import Lock
from typing import Any, Dict


_STORE: Dict[str, Dict[str, Any]] = {}
_LOCK = Lock()


def set_session_agent_meta(session_name: str, meta: Dict[str, Any]) -> None:
    key = (session_name or "").strip()
    if not key:
        return
    with _LOCK:
        _STORE[key] = dict(meta)


def get_session_agent_meta(session_name: str) -> Dict[str, Any]:
    key = (session_name or "").strip()
    if not key:
        return {}
    with _LOCK:
        value = _STORE.get(key)
        return dict(value) if isinstance(value, dict) else {}
