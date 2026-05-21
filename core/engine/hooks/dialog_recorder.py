from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_DIR = Path(
    os.environ.get("SKILLPILOT_AGENT_SESSION_DIR", REPO_ROOT / ".skillpilot" / "agent-sessions")
)
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid hook JSON on stdin: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("hook JSON on stdin must be an object")
    return value


def parse_args(default_event: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("codex", "claude", "gemini", "opencode"))
    parser.add_argument("--event", default=default_event)
    return parser.parse_args()


def infer_agent(payload: dict[str, Any]) -> str:
    hook_event = str(payload.get("hook_event_name") or "")
    transcript_path = str(payload.get("transcript_path") or "")
    if ".claude" in transcript_path or os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    if ".gemini" in transcript_path or hook_event in {
        "BeforeAgent",
        "AfterAgent",
        "AfterModel",
        "SessionEnd",
    } and "timestamp" in payload:
        return "gemini"
    if payload.get("event", {}).get("type") or str(payload.get("type") or "").startswith(
        ("session.", "message.", "tui.")
    ):
        return "opencode"
    return "codex"


def sanitize_component(value: Any, fallback: str) -> str:
    text = str(value or fallback).strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-._")
    return text[:120] or fallback


def session_id(payload: dict[str, Any]) -> str:
    event = payload.get("event")
    candidates = [
        payload.get("session_id"),
        payload.get("sessionID"),
        payload.get("sessionId"),
        payload.get("id"),
    ]
    if isinstance(event, dict):
        candidates.extend(
            [
                event.get("session_id"),
                event.get("sessionID"),
                event.get("sessionId"),
                event.get("session"),
                event.get("sessionID"),
                (event.get("properties") or {}).get("sessionID")
                if isinstance(event.get("properties"), dict)
                else None,
                (event.get("properties") or {}).get("session_id")
                if isinstance(event.get("properties"), dict)
                else None,
            ]
        )
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("id") or candidate.get("session_id")
        if candidate:
            return sanitize_component(candidate, "unknown-session")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return digest[:16]


def find_session_file(agent: str, sid: str) -> Path | None:
    if not SESSION_DIR.exists():
        return None
    matches = sorted(SESSION_DIR.glob(f"*-{sanitize_component(agent, 'agent')}-{sid}.jsonl"))
    return matches[0] if matches else None


def session_file(agent: str, sid: str, payload: dict[str, Any]) -> Path:
    existing = find_session_file(agent, sid)
    if existing:
        return existing
    timestamp = payload.get("timestamp")
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            stamp = format_timestamp(dt)
        except ValueError:
            stamp = format_timestamp()
    else:
        stamp = format_timestamp()
    return SESSION_DIR / f"{stamp}-{sanitize_component(agent, 'agent')}-{sid}.jsonl"


def text_from_content(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        pieces: list[str] = []
        for item in value:
            part = text_from_content(item)
            if part:
                pieces.append(part)
        text = "\n".join(pieces)
    elif isinstance(value, dict):
        if value.get("type") in {"tool_use", "tool_result", "function_call"}:
            return None
        for key in ("text", "content", "message", "value", "markdown"):
            part = text_from_content(value.get(key))
            if part:
                return part
        parts = value.get("parts")
        if parts is not None:
            return text_from_content(parts)
        return None
    else:
        return None
    text = text.strip()
    return text or None


def extract_user_prompt(payload: dict[str, Any]) -> str | None:
    for key in ("prompt", "user_prompt", "message", "input"):
        text = text_from_content(payload.get(key))
        if text:
            return text
    event = payload.get("event")
    if isinstance(event, dict):
        role = str(event.get("role") or event.get("author") or "").lower()
        message = event.get("message") if isinstance(event.get("message"), dict) else event
        if role == "user" or str(message.get("role") if isinstance(message, dict) else "").lower() == "user":
            return text_from_content(message)
    return None


def extract_agent_response(payload: dict[str, Any]) -> str | None:
    for key in ("last_assistant_message", "prompt_response", "assistant_response", "response"):
        text = text_from_content(payload.get(key))
        if text:
            return text
    response = payload.get("llm_response")
    if isinstance(response, dict):
        candidates = response.get("candidates")
        if isinstance(candidates, list):
            pieces: list[str] = []
            for candidate in candidates:
                content = candidate.get("content") if isinstance(candidate, dict) else None
                if isinstance(content, dict):
                    part = text_from_content(content.get("parts"))
                    if part:
                        pieces.append(part)
            if pieces:
                return "\n".join(pieces).strip()
    event = payload.get("event")
    if isinstance(event, dict):
        role = str(event.get("role") or event.get("author") or "").lower()
        message = event.get("message") if isinstance(event.get("message"), dict) else event
        message_role = str(message.get("role") if isinstance(message, dict) else "").lower()
        if role in {"assistant", "agent", "model"} or message_role in {"assistant", "agent", "model"}:
            return text_from_content(message)
    return None


def base_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "hook_event_name",
        "source",
        "cwd",
        "model",
        "permission_mode",
        "turn_id",
        "reason",
        "transcript_path",
    )
    return {key: payload[key] for key in keys if key in payload and payload[key] is not None}


def append_record(path: Path, record: dict[str, Any]) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def iter_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def has_record_type(path: Path, record_type: str) -> bool:
    return any(record.get("type") == record_type for record in iter_records(path))


def session_start_metadata(
    payload: dict[str, Any], extra_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    metadata = base_metadata(payload)
    if extra_metadata:
        metadata.update({key: value for key, value in extra_metadata.items() if value is not None})
    return metadata


def ensure_start_record(
    path: Path,
    agent: str,
    sid: str,
    payload: dict[str, Any],
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    append_record(
        path,
        {
            "type": "session_start",
            "timestamp": format_timestamp(),
            "agent": agent,
            "session_id": sid,
            "metadata": session_start_metadata(payload, extra_metadata),
            "inferred": True,
        },
    )


def extract_opencode_dialog(payload: dict[str, Any]) -> tuple[str, str] | None:
    event = payload.get("event")
    if not isinstance(event, dict) or event.get("type") != "message.part.updated":
        return None
    properties = event.get("properties")
    if not isinstance(properties, dict):
        return None
    part = properties.get("part")
    if not isinstance(part, dict) or part.get("type") != "text":
        return None
    text = text_from_content(part.get("text"))
    if not text:
        return None
    part_time = part.get("time")
    if isinstance(part_time, dict) and part_time.get("end") is not None:
        return "agent_response", text
    if "time" not in part:
        return "user_prompt", text
    return None


def opencode_has_session(payload: dict[str, Any]) -> bool:
    event = payload.get("event")
    if not isinstance(event, dict):
        return False
    properties = event.get("properties")
    if isinstance(properties, dict) and properties.get("sessionID"):
        return True
    return bool(event.get("sessionID") or event.get("session_id") or event.get("sessionId"))


def record_event(default_event: str, extra_metadata: dict[str, Any] | None = None) -> None:
    args = parse_args(default_event)
    payload = read_stdin_json()
    agent = args.agent or infer_agent(payload)
    if agent == "opencode" and not opencode_has_session(payload):
        print("{}")
        return
    sid = session_id(payload)
    path = session_file(agent, sid, payload)

    event = args.event
    if event == "session_start":
        if has_record_type(path, "session_start"):
            print("{}")
            return
        append_record(
            path,
            {
                "type": "session_start",
                "timestamp": format_timestamp(),
                "agent": agent,
                "session_id": sid,
                "metadata": session_start_metadata(payload, extra_metadata),
            },
        )
        print("{}")
        return

    ensure_start_record(path, agent, sid, payload)
    if agent == "opencode":
        opencode_dialog = extract_opencode_dialog(payload)
        if opencode_dialog:
            record_type, content = opencode_dialog
            append_record(
                path,
                {
                    "type": record_type,
                    "timestamp": format_timestamp(),
                    "agent": agent,
                    "session_id": sid,
                    "content": content,
                    "metadata": base_metadata(payload),
                },
            )
        if event == "opencode_event":
            print("{}")
            return

    if event == "user_prompt":
        content = extract_user_prompt(payload)
        record_type = "user_prompt"
    elif event == "agent_stop":
        content = extract_agent_response(payload)
        record_type = "agent_response"
    elif event == "session_end":
        if has_record_type(path, "session_end"):
            print("{}")
            return
        append_record(
            path,
            {
                "type": "session_end",
                "timestamp": format_timestamp(),
                "agent": agent,
                "session_id": sid,
                "metadata": base_metadata(payload),
            },
        )
        print("{}")
        return
    else:
        content = None
        record_type = event

    if content:
        append_record(
            path,
            {
                "type": record_type,
                "timestamp": format_timestamp(),
                "agent": agent,
                "session_id": sid,
                "content": content,
                "metadata": base_metadata(payload),
            },
        )
    print("{}")
