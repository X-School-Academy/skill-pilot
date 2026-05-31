from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_DIR = Path(
    os.environ.get("SKILLPILOT_AGENT_SESSION_DIR", REPO_ROOT / ".skillpilot" / "agent-sessions")
)
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
SESSION_FILE_RE = re.compile(r"^[^/\\]+\.jsonl$")
SUPPORTED_RESUME_AGENTS = {"codex", "claude", "gemini", "opencode"}
PATH_TOKEN_RE = re.compile(r"(?<![\w@])@?(?:/|\.?/)?[A-Za-z0-9_.-]+(?:/[^\s`\"'<>]+)+")


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def display_time(value: Any) -> str:
    parsed = parse_timestamp(value)
    if parsed is None:
        return str(value or "")
    return parsed.isoformat().replace("+00:00", "Z")


def _strip_path_token(value: str) -> str:
    text = value.strip().strip("`\"'<>")
    text = text.rstrip(".,;:!?)]}")
    text = text.lstrip("([{")
    if re.search(r":\d+(?::\d+)?$", text):
        text = re.sub(r":\d+(?::\d+)?$", "", text)
    return text.strip()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _candidate_path(token: str, repo_root: Path) -> Path | None:
    text = _strip_path_token(token)
    if not text:
        return None
    if text.startswith("@"):
        text = text[1:]

    raw_path = Path(text).expanduser()
    if raw_path.is_absolute():
        path = raw_path.resolve(strict=False)
    else:
        while text.startswith("./"):
            text = text[2:]
        if text.startswith("../") or text == "..":
            return None
        path = (repo_root / text).resolve(strict=False)

    root = repo_root.resolve(strict=False)
    if not _is_relative_to(path, root):
        return None
    return path


def infer_session_category(prompt: str | None, repo_root: Path = REPO_ROOT) -> str:
    if not prompt:
        return "/"
    for match in PATH_TOKEN_RE.finditer(prompt):
        path = _candidate_path(match.group(0), repo_root)
        if path is None or not path.exists():
            continue
        if path.is_dir():
            return path.name or "/"
        parent = path.parent
        root = repo_root.resolve(strict=False)
        if parent == root:
            return "/"
        return parent.name or "/"
    return "/"


def infer_session_category_from_directory(directory: str | None, repo_root: Path = REPO_ROOT) -> str:
    text = _strip_path_token(str(directory or ""))
    if not text:
        return "/"
    if text.startswith("@"):
        text = text[1:]

    raw_path = Path(text).expanduser()
    if raw_path.is_absolute():
        path = raw_path.resolve(strict=False)
    else:
        while text.startswith("./"):
            text = text[2:]
        if text.startswith("../") or text == "..":
            return "/"
        path = (repo_root / text).resolve(strict=False)

    if path.is_file():
        path = path.parent

    root = repo_root.resolve(strict=False)
    if path == root:
        return "/"
    return path.name or "/"


def iter_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
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


def _first_content(records: list[dict[str, Any]], record_type: str) -> str:
    for record in records:
        if record.get("type") == record_type and record.get("content"):
            return str(record["content"])
    return ""


def _session_category(records: list[dict[str, Any]], first_prompt: str) -> str:
    for record in records:
        if record.get("type") == "session_category":
            category = str(record.get("category") or "").strip()
            if category:
                return category
    return infer_session_category(first_prompt)


def _session_model(records: list[dict[str, Any]]) -> str:
    for record in records:
        metadata = record.get("metadata")
        if isinstance(metadata, dict) and metadata.get("model"):
            return str(metadata["model"])
        if record.get("type") == "model_info" and record.get("model"):
            return str(record["model"])
    return ""


def _last_timestamp(records: list[dict[str, Any]]) -> str:
    best: datetime | None = None
    raw = ""
    for record in records:
        stamp = record.get("timestamp")
        parsed = parse_timestamp(stamp)
        if parsed is None:
            continue
        if best is None or parsed > best:
            best = parsed
            raw = str(stamp)
    return display_time(raw)


def summarize_session(path: Path) -> dict[str, Any] | None:
    records = iter_records(path)
    if not records:
        return None
    first_prompt = _first_content(records, "user_prompt")
    agent = ""
    session_id = ""
    for record in records:
        if not agent and record.get("agent"):
            agent = str(record["agent"])
        if not session_id and record.get("session_id"):
            session_id = str(record["session_id"])
        if agent and session_id:
            break
    category = _session_category(records, first_prompt)
    latest_time = _last_timestamp(records)
    return {
        "id": path.name,
        "file": path.name,
        "category": category or "/",
        "title": first_prompt,
        "agent": agent,
        "model": _session_model(records),
        "session_id": session_id,
        "time": latest_time,
        "resume_supported": agent in SUPPORTED_RESUME_AGENTS and bool(session_id),
    }


def list_agent_session_categories(session_dir: Path = SESSION_DIR) -> list[dict[str, Any]]:
    if not session_dir.is_dir():
        return []
    sessions: list[dict[str, Any]] = []
    for path in sorted(session_dir.glob("*.jsonl")):
        summary = summarize_session(path)
        if summary is not None and summary.get("title"):
            sessions.append(summary)

    sessions.sort(key=lambda item: item.get("time") or "", reverse=True)
    by_category: dict[str, dict[str, Any]] = {}
    for session in sessions:
        category = str(session.get("category") or "/")
        entry = by_category.setdefault(category, {"name": category, "time": "", "sessions": []})
        entry["sessions"].append(session)
        if str(session.get("time") or "") > str(entry.get("time") or ""):
            entry["time"] = session.get("time") or ""

    categories = list(by_category.values())
    categories.sort(key=lambda item: str(item.get("time") or ""), reverse=True)
    return categories


def resolve_session_path(session_id: str, session_dir: Path = SESSION_DIR) -> Path:
    safe_id = Path(str(session_id or "")).name
    if not SESSION_FILE_RE.fullmatch(safe_id):
        raise ValueError("invalid agent session id")
    path = (session_dir / safe_id).resolve(strict=False)
    root = session_dir.resolve(strict=False)
    if not _is_relative_to(path, root):
        raise ValueError("invalid agent session id")
    if not path.is_file():
        raise FileNotFoundError(f"agent session not found: {safe_id}")
    return path


def render_session_markdown(path: Path) -> tuple[dict[str, Any], str]:
    records = iter_records(path)
    summary = summarize_session(path) or {"id": path.name, "agent": "", "model": "", "time": ""}
    lines: list[str] = ["# Agent history", ""]
    if summary.get("agent"):
        lines.append(f"- agent: {summary['agent']}")
    if summary.get("model"):
        lines.append(f"- model: {summary['model']}")
    if summary.get("time"):
        lines.append(f"- time: {summary['time']}")
    lines.append("")

    for record in records:
        rtype = record.get("type")
        content = record.get("content")
        if rtype == "user_prompt" and content:
            lines.append("## user_prompt")
            lines.append("")
            lines.append(str(content).rstrip())
            lines.append("")
        elif rtype == "agent_response" and content:
            lines.append("## agent_response")
            lines.append("")
            lines.append(str(content).rstrip())
            lines.append("")

    return summary, "\n".join(lines).rstrip() + "\n"


def read_agent_session_payload(session_id: str, session_dir: Path = SESSION_DIR) -> dict[str, Any]:
    path = resolve_session_path(session_id, session_dir=session_dir)
    summary, markdown = render_session_markdown(path)
    return {"session": summary, "markdown": markdown}
