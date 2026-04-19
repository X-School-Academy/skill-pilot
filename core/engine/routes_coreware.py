from routes_shared import *

from worktree_utils import (
    create_worktree,
    git_command,
    list_worktrees,
    remove_worktree,
    sanitize_worktree_suffix,
    worktree_path_for_suffix,
)


_ABOUT_VERSION_PATH = _REPO_ROOT / "about" / "version.json5"
_WORKSPACE_PATH = _REPO_ROOT / "workspace"
_SAMPLE_WORKSPACE_REMOTE = "https://github.com/X-School-Academy/skill-pilot_workspace.git"


def _coreware_branch_name(suffix: str) -> str:
    timestamp = int(time.time())
    return f"coreware/{suffix}-{timestamp}"


@router.get("/api/coreware/about")
def coreware_about():
    try:
        raw = _ABOUT_VERSION_PATH.read_text(encoding="utf-8")
        data = json5.loads(raw)
        return {
            "version": str(data.get("version") or ""),
            "build": data.get("build"),
            "path": str(_ABOUT_VERSION_PATH.relative_to(_REPO_ROOT)),
            "runtime_mode": get_runtime_mode(),
        }
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "about/version.json5 not found"})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/coreware/dev/start")
def coreware_dev_start(payload: Dict[str, Any] | None = None):
    if get_runtime_mode() == "development":
        return JSONResponse(
            status_code=400,
            content={"error": "Already running in development mode"},
        )
    try:
        import routes as routes_root  # lazy to avoid circular import at module load
        routes_root._spawn_skillpilot_dev_start(_REPO_ROOT)
        return {"status": "launched", "dev_url": routes_root._explore_dev_base_url()}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/coreware/dev/status")
def coreware_dev_status():
    try:
        import routes as routes_root
        dev_url = routes_root._explore_dev_base_url()
        ready = bool(routes_root._probe_explore_dev_ready())
        return {"ready": ready, "dev_url": dev_url}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/coreware/workspace/remote")
def coreware_workspace_remote():
    try:
        if not _WORKSPACE_PATH.is_dir():
            return JSONResponse(status_code=404, content={"error": "workspace folder not found"})
        proc = git_command(["remote", "get-url", "origin"], cwd=_WORKSPACE_PATH, check=False)
        url = proc.stdout.strip() if proc.returncode == 0 else ""
        return {
            "url": url,
            "is_sample": url == _SAMPLE_WORKSPACE_REMOTE,
            "sample_url": _SAMPLE_WORKSPACE_REMOTE,
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


def _worktree_entry_for_response(entry: Dict[str, Any]) -> Dict[str, Any]:
    path_str = str(entry.get("path") or "")
    path_obj = Path(path_str) if path_str else None
    name = path_obj.name if path_obj else ""
    repo_prefix = f"{_REPO_ROOT.name}_"
    display_name = name[len(repo_prefix):] if name.startswith(repo_prefix) else name
    branch = str(entry.get("branch") or "")
    if branch.startswith("refs/heads/"):
        branch = branch[len("refs/heads/"):]
    return {
        "path": path_str,
        "name": display_name or name,
        "branch": branch,
        "head": str(entry.get("head") or ""),
        "is_main": path_obj is not None and path_obj.resolve() == _REPO_ROOT.resolve(),
        "detached": bool(entry.get("detached")),
    }


@router.get("/api/coreware/worktrees")
def coreware_worktrees_list():
    try:
        entries = list_worktrees()
        return {"items": [_worktree_entry_for_response(item) for item in entries]}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "items": []})


@router.post("/api/coreware/worktrees/create")
def coreware_worktrees_create(payload: Dict[str, Any]):
    raw_name = str(payload.get("name") or "").strip()
    if not raw_name:
        return JSONResponse(status_code=400, content={"error": "Worktree name is required"})

    suffix = sanitize_worktree_suffix(raw_name)
    target_path = worktree_path_for_suffix(suffix)
    if target_path.exists():
        return JSONResponse(
            status_code=409,
            content={"error": f"Worktree path already exists: {target_path}", "path": str(target_path)},
        )

    try:
        create_worktree(target_path, branch_name=_coreware_branch_name(suffix))
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok", "path": str(target_path), "name": suffix}


@router.post("/api/coreware/worktrees/remove")
def coreware_worktrees_remove(payload: Dict[str, Any]):
    raw_path = str(payload.get("path") or "").strip()
    if not raw_path:
        return JSONResponse(status_code=400, content={"error": "Worktree path is required"})

    target_path = Path(raw_path).resolve()
    if target_path == _REPO_ROOT.resolve():
        return JSONResponse(status_code=400, content={"error": "Refusing to remove the main repo worktree"})

    # Only allow removal of worktrees sitting next to the main repo with the expected prefix.
    expected_parent = _REPO_ROOT.parent.resolve()
    if target_path.parent != expected_parent or not target_path.name.startswith(f"{_REPO_ROOT.name}_"):
        return JSONResponse(
            status_code=400,
            content={"error": "Refusing to remove a worktree outside the managed location"},
        )

    try:
        remove_worktree(target_path)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok", "path": str(target_path)}
