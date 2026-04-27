from __future__ import annotations

from pathlib import Path


def load_agents_md(agent_dir: Path) -> str:
    root = agent_dir.resolve()
    if not root.exists():
        return ""

    path = root / "AGENTS.md"
    try:
        content = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""
    if not content:
        return ""
    return f"# Root AGENTS.md Instructions\n\n## AGENTS.md\n\n{content}"
