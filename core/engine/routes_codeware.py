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
_WEBUI_BUILD_COMMIT_MESSAGE = "rebuild webui - by webui action"


def _run_codeware_command(args: List[str], *, cwd: Path, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["./skillpilot.sh", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=False,
        env=safe_env(),
        timeout=timeout,
    )
    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(message or f"skillpilot command failed: {' '.join(args)}")
    return proc


def _spawn_codeware_prod_restart(target_root: Path) -> Path:
    log_dir = target_root / ".skillpilot" / "temp"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "codeware-prod-restart.log"
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            ["bash", "-lc", "sleep 1 && exec ./skillpilot.sh start --source webui"],
            cwd=str(target_root),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=safe_env(),
            start_new_session=True,
            close_fds=True,
        )
    return log_path


def _commit_rebuilt_webui_assets() -> Dict[str, Any]:
    webui_www_rel = "core/webui/www"
    git_command(["add", webui_www_rel], cwd=_REPO_ROOT)
    diff_proc = git_command(["diff", "--cached", "--quiet", "--", webui_www_rel], cwd=_REPO_ROOT, check=False)
    if diff_proc.returncode == 0:
        return {
            "committed": False,
            "message": "WebUI build completed. No changes in core/webui/www to commit.",
        }
    git_command(["commit", "-m", _WEBUI_BUILD_COMMIT_MESSAGE, "--", webui_www_rel], cwd=_REPO_ROOT)
    return {
        "committed": True,
        "message": _WEBUI_BUILD_COMMIT_MESSAGE,
    }


def _codeware_branch_name(suffix: str) -> str:
    timestamp = int(time.time())
    return f"codeware/{suffix}-{timestamp}"


@router.get("/api/codeware/about")
def codeware_about():
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


@router.post("/api/codeware/dev/start")
def codeware_dev_start(payload: Dict[str, Any] | None = None):
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


@router.get("/api/codeware/dev/status")
def codeware_dev_status():
    try:
        import routes as routes_root
        dev_url = routes_root._explore_dev_base_url()
        ready = bool(routes_root._probe_explore_dev_ready())
        return {"ready": ready, "dev_url": dev_url}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/api/codeware/prod/restart")
def codeware_prod_restart(payload: Dict[str, Any] | None = None):
    if get_runtime_mode() != "production":
        return JSONResponse(
            status_code=400,
            content={"error": "Restart Skill Pilot is only available from production mode"},
        )

    rebuild_webui = bool((payload or {}).get("rebuild_webui"))
    try:
        build_commit: Dict[str, Any] | None = None
        if rebuild_webui:
            _run_codeware_command(["build"], cwd=_REPO_ROOT, timeout=1800.0)
            build_commit = _commit_rebuilt_webui_assets()
        log_path = _spawn_codeware_prod_restart(_REPO_ROOT)
        host, port = get_service_host_port("engine", mode="production", default_host="127.0.0.1", default_port=8001)
        return {
            "status": "restarting",
            "rebuild_webui": rebuild_webui,
            "target_url": f"http://{host}:{port}",
            "log_path": str(log_path),
            "build_commit": build_commit,
        }
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/api/codeware/workspace/remote")
def codeware_workspace_remote():
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


@router.get("/api/codeware/worktrees")
def codeware_worktrees_list():
    try:
        entries = list_worktrees()
        return {"items": [_worktree_entry_for_response(item) for item in entries]}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc), "items": []})


@router.post("/api/codeware/worktrees/create")
def codeware_worktrees_create(payload: Dict[str, Any]):
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
        create_worktree(target_path, branch_name=_codeware_branch_name(suffix))
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

    return {"status": "ok", "path": str(target_path), "name": suffix}


@router.post("/api/codeware/worktrees/remove")
def codeware_worktrees_remove(payload: Dict[str, Any]):
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
