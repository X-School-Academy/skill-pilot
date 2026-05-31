from __future__ import annotations

import subprocess
from pathlib import Path

from dialog_recorder import REPO_ROOT, record_event


def current_git_commit(repo_root: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit or None


if __name__ == "__main__":
    record_event("session_start", extra_metadata={"git_commit": current_git_commit()})
