from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_DIR = Path(
    os.environ.get("SKILLPILOT_AGENT_SESSION_DIR", REPO_ROOT / ".skillpilot" / "agent-sessions")
)


def resolve_session_file(arg: str) -> Path:
    candidate = Path(arg)
    if candidate.is_absolute() and candidate.is_file():
        return candidate

    rel = REPO_ROOT / arg
    if rel.is_file():
        return rel

    in_session_dir = SESSION_DIR / arg
    if in_session_dir.is_file():
        return in_session_dir

    if SESSION_DIR.exists():
        matches = sorted(SESSION_DIR.glob(f"*{arg}*"))
        matches = [m for m in matches if m.is_file() and m.suffix == ".jsonl"]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            listing = "\n  ".join(str(m.relative_to(REPO_ROOT)) for m in matches)
            raise SystemExit(f"ambiguous match for '{arg}':\n  {listing}")

    raise SystemExit(f"no session file found for '{arg}' (looked in {SESSION_DIR})")


def iter_records(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield value


def render(path: Path) -> str:
    records = list(iter_records(path))

    git_commit = ""
    model = ""
    agent = ""
    for record in records:
        metadata = record.get("metadata") or {}
        if not git_commit and metadata.get("git_commit"):
            git_commit = str(metadata["git_commit"])
        if not model and metadata.get("model"):
            model = str(metadata["model"])
        if not agent and record.get("agent"):
            agent = str(record["agent"])
        if git_commit and model and agent:
            break

    lines: list[str] = ["# Agent history", ""]
    lines.append(
        "This session was recorded against a specific git commit. "
        "To reproduce the work, check out that commit and replay the user prompts below:"
    )
    lines.append("")
    lines.append(f"    git checkout {git_commit}" if git_commit else "    git checkout <commit>")
    lines.append("")
    lines.append(f"- commit: {git_commit}")
    if agent:
        lines.append(f"- agent: {agent}")
    if model and agent in {"codex", "claude"}:
        lines.append(f"- model: {model}")
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

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export an agent session jsonl file as human-readable markdown.",
    )
    parser.add_argument(
        "target",
        help=(
            "Session reference: path relative to repo root, file name only, "
            "or a session id substring."
        ),
    )
    args = parser.parse_args()

    path = resolve_session_file(args.target)
    sys.stdout.write(render(path))


if __name__ == "__main__":
    main()
