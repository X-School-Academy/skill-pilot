"""Shared git worktree helpers used by Explore (showcase templates) and Codeware."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from routes_shared import _CONFIG_ENV_PATH, _REPO_ROOT, safe_env


def git_command(
    args: List[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        shell=False,
        env=safe_env(),
    )
    if check and proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"git command failed: {' '.join(args)}")
    return proc


def sanitize_worktree_suffix(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value or "").strip("_")
    return cleaned or "sample"


def worktree_path_for_suffix(suffix: str, *, repo_root: Path = _REPO_ROOT) -> Path:
    """Returns `<repo_root.parent>/<repo_root.name>_<suffix>`."""
    return repo_root.parent / f"{repo_root.name}_{suffix}"


def repo_has_local_changes(repo_path: Path) -> bool:
    proc = git_command(["status", "--porcelain", "--untracked-files=all"], cwd=repo_path)
    return bool(proc.stdout.strip())


def push_worktree_stash(repo_path: Path, message: str) -> str | None:
    if not repo_has_local_changes(repo_path):
        return None
    before = git_command(
        ["rev-parse", "-q", "--verify", "refs/stash"], cwd=repo_path, check=False
    ).stdout.strip()
    proc = git_command(["stash", "push", "-u", "-m", message], cwd=repo_path, check=False)
    if proc.returncode != 0:
        message_out = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message_out or "Failed to stash local changes before creating worktree")
    after = git_command(
        ["rev-parse", "-q", "--verify", "refs/stash"], cwd=repo_path, check=False
    ).stdout.strip()
    if not after or after == before:
        return None
    return "stash@{0}"


def apply_and_drop_stash_for_worktree(
    repo_path: Path, worktree_path: Path, stash_ref: str
) -> None:
    git_command(["stash", "apply", stash_ref], cwd=worktree_path)
    git_command(["stash", "apply", stash_ref], cwd=repo_path)
    git_command(["stash", "drop", stash_ref], cwd=repo_path)


def restore_stash_to_repo(repo_path: Path, stash_ref: str) -> None:
    try:
        git_command(["stash", "apply", stash_ref], cwd=repo_path)
    finally:
        git_command(["stash", "drop", stash_ref], cwd=repo_path, check=False)


def ensure_worktree_config_symlink(worktree_path: Path) -> None:
    source = _CONFIG_ENV_PATH.parent
    target = worktree_path / "config"
    if target.is_symlink():
        if os.path.realpath(target) == str(source):
            return
        target.unlink()
    elif target.exists():
        raise RuntimeError(f"Refusing to replace non-symlink config at: {target}")
    rel_source = os.path.relpath(source, start=target.parent)
    target.symlink_to(rel_source, target_is_directory=True)


def commit_worktree_config_if_changed(
    worktree_path: Path,
    *,
    message: str = "Track shared config symlink",
) -> bool:
    git_command(["add", "--", "config"], cwd=worktree_path)
    proc = git_command(
        ["diff", "--cached", "--quiet", "--", "config"],
        cwd=worktree_path,
        check=False,
    )
    if proc.returncode == 0:
        return False
    if proc.returncode != 1:
        output = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(output or "Failed to check staged config changes")

    git_command(["commit", "-m", message, "--", "config"], cwd=worktree_path)
    return True


def create_worktree(
    path: Path,
    *,
    branch_name: str,
    base_ref: str | None = None,
    repo_root: Path = _REPO_ROOT,
    stash_message: str = "save local changes",
) -> None:
    """Create a git worktree at `path` on new branch `branch_name`.

    Preserves local changes via stash and symlinks `config/` to keep env shared.
    """
    stash_ref: str | None = None
    try:
        stash_ref = push_worktree_stash(repo_root, stash_message)
        args = ["worktree", "add", "-b", branch_name, str(path)]
        if base_ref:
            args.append(base_ref)
        git_command(args, cwd=repo_root)
        if stash_ref:
            apply_and_drop_stash_for_worktree(repo_root, path, stash_ref)
            stash_ref = None
        ensure_worktree_config_symlink(path)
        commit_worktree_config_if_changed(path)
    except Exception:
        if stash_ref:
            restore_stash_to_repo(repo_root, stash_ref)
        raise


def remove_worktree(path: Path, *, repo_root: Path = _REPO_ROOT) -> None:
    if not path.exists():
        return
    proc = git_command(
        ["-C", str(repo_root), "worktree", "remove", "--force", str(path)], check=False
    )
    if proc.returncode == 0:
        return
    shutil.rmtree(path)


def list_worktrees(*, repo_root: Path = _REPO_ROOT) -> List[Dict[str, Any]]:
    """Parse `git worktree list --porcelain` into a list of entries."""
    proc = git_command(["worktree", "list", "--porcelain"], cwd=repo_root)
    entries: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    for raw_line in proc.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line[len("worktree "):].strip()
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):].strip()
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True
    if current:
        entries.append(current)
    return entries
