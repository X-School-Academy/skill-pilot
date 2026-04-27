from __future__ import annotations

from pathlib import Path


def load_agents_md(agent_dir: Path, agent_file: Path | str | None = None) -> str:
    """Load the agent instructions file once, without recursion.

    - ``agent_file`` may be ``None`` (default ``AGENTS.md`` under ``agent_dir``),
      a relative path resolved against ``agent_dir``, or an absolute path.
    - If the resolved file is missing or empty, returns an empty string.
    """
    root = Path(agent_dir).resolve()
    if agent_file is None:
        path = root / "AGENTS.md"
    else:
        candidate = Path(agent_file)
        path = candidate if candidate.is_absolute() else (root / candidate)
    path = path.resolve()

    try:
        content = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""
    if not content:
        return ""
    return f"# Root {path.name} Instructions\n\n## {path.name}\n\n{content}"
