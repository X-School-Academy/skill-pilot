#!/bin/sh
""":"
if [ ! -x core/engine/.venv/bin/python ]; then
    echo "Run this script from the Skill Pilot project root." >&2
    echo "Expected executable: core/engine/.venv/bin/python" >&2
    exit 1
fi
exec core/engine/.venv/bin/python "$0" "$@"
":"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT_MARKERS = ("core/bin", "core/engine", "core/skills")
PATH_RE = re.compile(r"(?<![\w@])@?(?:/|\.?/)?[A-Za-z0-9_.-]+(?:/[^\s`\"'<>]+)+")


def is_repo_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in ROOT_MARKERS)


def parents_inclusive(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        path = path.parent
    return [path, *path.parents]


def find_repo_root(session_arg: str) -> Path:
    candidates: list[Path] = []
    raw_session = Path(session_arg).expanduser()
    if raw_session.is_absolute():
        candidates.extend(parents_inclusive(raw_session))
    else:
        candidates.extend(parents_inclusive(Path.cwd() / raw_session))
        candidates.extend(parents_inclusive(Path.cwd()))
    candidates.extend(parents_inclusive(Path(__file__)))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_repo_root(candidate):
            return candidate
    raise SystemExit(
        "Could not find the Skill Pilot repo root. Expected a parent directory "
        "containing core/bin, core/engine, and core/skills."
    )


def resolve_session_file(repo_root: Path, session_arg: str) -> Path:
    raw = Path(session_arg).expanduser()
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, repo_root / raw]
    if not raw.is_absolute() and raw.name == session_arg:
        candidates.append(repo_root / ".skillpilot" / "agent-sessions" / session_arg)
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved.is_file():
            return resolved
    raise SystemExit(f"Session file not found: {session_arg}")


def compact_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}... [truncated {len(text) - limit} chars]"


def load_records(path: Path) -> list[dict[str, Any]]:
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


def first_value(records: list[dict[str, Any]], *keys: str) -> str:
    for record in records:
        for key in keys:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        metadata = record.get("metadata")
        if isinstance(metadata, dict):
            for key in keys:
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def extract_paths(records: list[dict[str, Any]], limit: int) -> list[str]:
    paths: Counter[str] = Counter()
    for record in records:
        content = record.get("content")
        if not isinstance(content, str):
            continue
        for match in PATH_RE.finditer(content):
            token = match.group(0).strip().strip("`\"'<>").rstrip(".,;:!?)]}")
            if token:
                paths[token] += 1
    return [path for path, _count in paths.most_common(limit)]


def small_metadata(record: dict[str, Any]) -> dict[str, Any]:
    excluded = {"content", "delta", "text", "message"}
    result: dict[str, Any] = {}
    for key, value in record.items():
        if key in excluded:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        elif isinstance(value, dict):
            result[key] = {
                inner_key: inner_value
                for inner_key, inner_value in value.items()
                if isinstance(inner_value, (str, int, float, bool)) or inner_value is None
            }
    return result


def render_markdown(path: Path, records: list[dict[str, Any]], prompt_limit: int, response_limit: int, max_turns: int) -> str:
    type_counts = Counter(str(record.get("type") or "unknown") for record in records)
    agent = first_value(records, "agent")
    session_id = first_value(records, "session_id")
    model = first_value(records, "model")
    category = first_value(records, "category")
    showcase_id = first_value(records, "showcase_id")
    showcase_directory = first_value(records, "showcase_directory")

    lines = [
        "# Compact Agent Session Context",
        "",
        "## Session",
        "",
        f"- jsonl_file: {path}",
        f"- records: {len(records)}",
    ]
    if agent:
        lines.append(f"- agent: {agent}")
    if session_id:
        lines.append(f"- session_id: {session_id}")
    if model:
        lines.append(f"- model: {model}")
    if category:
        lines.append(f"- category: {category}")
    if showcase_id:
        lines.append(f"- showcase_id: {showcase_id}")
    if showcase_directory:
        lines.append(f"- showcase_directory: {showcase_directory}")

    lines.extend(["", "## Record Types", ""])
    for record_type, count in type_counts.most_common():
        lines.append(f"- {record_type}: {count}")

    metadata_records = [
        small_metadata(record)
        for record in records
        if record.get("type") not in {"user_prompt", "agent_response"} and small_metadata(record)
    ]
    if metadata_records:
        lines.extend(["", "## Metadata Records", ""])
        for item in metadata_records[:20]:
            lines.append(f"- {json.dumps(item, ensure_ascii=False, sort_keys=True)}")
        if len(metadata_records) > 20:
            lines.append(f"- ... {len(metadata_records) - 20} more metadata records omitted")

    paths = extract_paths(records, 30)
    if paths:
        lines.extend(["", "## Referenced Paths", ""])
        for item in paths:
            lines.append(f"- {item}")

    lines.extend(["", "## Dialog Turns", ""])
    turns = 0
    for record in records:
        record_type = record.get("type")
        content = record.get("content")
        if record_type not in {"user_prompt", "agent_response"} or not content:
            continue
        turns += 1
        if turns > max_turns:
            remaining = sum(
                1
                for item in records
                if item.get("type") in {"user_prompt", "agent_response"} and item.get("content")
            ) - max_turns
            lines.append(f"- ... {remaining} more dialog records omitted")
            break
        label = "User Prompt" if record_type == "user_prompt" else "Agent Response"
        limit = prompt_limit if record_type == "user_prompt" else response_limit
        timestamp = record.get("timestamp") or ""
        suffix = f" ({timestamp})" if timestamp else ""
        lines.extend([f"### {turns}. {label}{suffix}", "", compact_text(content, limit), ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract compact context from an agent session JSONL file.")
    parser.add_argument("jsonl_file", help="Path to the agent session .jsonl file")
    parser.add_argument("--prompt-limit", type=int, default=1600, help="Maximum characters per user prompt")
    parser.add_argument("--response-limit", type=int, default=900, help="Maximum characters per agent response")
    parser.add_argument("--max-turns", type=int, default=80, help="Maximum dialog records to output")
    args = parser.parse_args()

    repo_root = find_repo_root(args.jsonl_file)
    path = resolve_session_file(repo_root, args.jsonl_file)
    records = load_records(path)
    print(render_markdown(path, records, args.prompt_limit, args.response_limit, args.max_turns), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
