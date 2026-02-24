import os
from pathlib import Path


_STAGE_DIR_MARKERS = ("00-init-ideas", "01-market-research", "10-sprints")


def _looks_like_project_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in _STAGE_DIR_MARKERS)


def get_project_root() -> Path:
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        return Path(project_root).expanduser().resolve()
    # Search upward from this file so path refactors do not break stage roots.
    current = Path(__file__).resolve()
    for parent in current.parents:
        if _looks_like_project_root(parent):
            return parent
    # Fallback: core/engine/dev_swarm/project.py -> repo root
    return current.parents[3]
