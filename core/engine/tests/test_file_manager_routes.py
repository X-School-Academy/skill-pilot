import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes
import routes_file_manager
import routes_shared
import session_agent_store
from file_realtime import FileRealtimeHub, path_within_scope


def _set_repo_root(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(routes, "_REPO_ROOT", root)
    monkeypatch.setattr(routes, "_REPO_ROOT_RESOLVED", root.resolve())


def test_files_list_includes_hidden_files_and_protected_names(monkeypatch, tmp_path: Path):
    (tmp_path / ".gitignore").write_text("node_modules\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / ".env").write_text("SECRET=1\n", encoding="utf-8")

    _set_repo_root(monkeypatch, tmp_path)

    root_listing = routes.files_list("/")
    assert isinstance(root_listing, dict)
    root_ids = {entry["id"] for entry in root_listing["data"]}
    assert "/.gitignore" in root_ids
    assert "/config" in root_ids

    config_listing = routes.files_list("/config")
    assert isinstance(config_listing, dict)
    config_ids = {entry["id"] for entry in config_listing["data"]}
    assert "/config/.env" in config_ids


def test_files_read_denies_protected_env_but_allows_other_hidden_files(monkeypatch, tmp_path: Path):
    (tmp_path / ".gitignore").write_text("dist\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / ".env").write_text("SECRET=1\n", encoding="utf-8")

    _set_repo_root(monkeypatch, tmp_path)

    hidden_file_response = routes.files_read("/.gitignore")
    assert isinstance(hidden_file_response, dict)
    assert hidden_file_response["content"] == "dist\n"

    protected_response = routes.files_read("/config/.env")
    assert protected_response.status_code == 403
    assert json.loads(protected_response.body.decode("utf-8")) == {"error": "Permission denied"}


def test_files_list_preserves_symlink_alias_paths(monkeypatch, tmp_path: Path):
    (tmp_path / ".agentignore").write_text("node_modules\n", encoding="utf-8")
    (tmp_path / ".codexignore").symlink_to(".agentignore")
    (tmp_path / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").symlink_to("AGENTS.md")

    _set_repo_root(monkeypatch, tmp_path)

    root_listing = routes.files_list("/")
    assert isinstance(root_listing, dict)
    root_ids = [entry["id"] for entry in root_listing["data"]]

    assert "/.agentignore" in root_ids
    assert "/.codexignore" in root_ids
    assert root_ids.count("/.agentignore") == 1
    assert root_ids.count("/.codexignore") == 1
    assert "/AGENTS.md" in root_ids
    assert "/CLAUDE.md" in root_ids
    assert root_ids.count("/AGENTS.md") == 1
    assert root_ids.count("/CLAUDE.md") == 1


def test_file_realtime_scope_matching():
    assert path_within_scope("/config/.env", "/", None) is True
    assert path_within_scope("/config/.env", "/config", None) is True
    assert path_within_scope("/config/.env", "/docs", None) is False
    assert path_within_scope("/config/.env", "/docs", "/config/.env") is True


def test_terminal_env_accepts_key_value_array():
    assert routes._coerce_terminal_env([["SHOWCASE_SESSION_DIRECTORY", "/tmp/showcase"]]) == {
        "SHOWCASE_SESSION_DIRECTORY": "/tmp/showcase",
    }


def test_prompt_target_url_includes_showcase_directory_and_file_manager_path(monkeypatch, tmp_path: Path):
    directory = tmp_path / "workspace" / "tasks" / "aws-credentials-s3-cloudfront"
    directory.mkdir(parents=True)
    _set_repo_root(monkeypatch, tmp_path)

    url = routes._build_prompt_target_url("", "do work", showcase_directory=str(directory))
    query = parse_qs(urlparse(url).query)

    assert query["new"] == ["true"]
    assert query["prompt"] == ["do work"]
    assert query["showcaseDirectory"] == [str(directory)]
    assert query["fileManagerPath"] == ["/workspace/tasks/aws-credentials-s3-cloudfront"]


def test_file_realtime_status_reports_unhealthy_state(tmp_path: Path):
    hub = FileRealtimeHub(
        tmp_path,
        skip_dir_names=set(),
        normalize_path=lambda path: "/" + path.name,
    )
    hub._record_error("watch failed")
    status = hub.status()
    assert status["healthy"] is False
    assert status["last_error"] == "watch failed"
    assert status["thread_alive"] is False


def test_workflow_execute_thread_uses_shared_terminal_base_dir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(routes_shared, "_REPO_ROOT", tmp_path)

    helper = routes_shared._execute_workflow_in_terminal_thread.__globals__.get("_terminal_workflow_base_dir")

    assert helper is routes_shared._terminal_workflow_base_dir
    assert helper() == tmp_path / ".skillpilot" / "temp" / "terminal-workflow"


def test_terminal_start_dir_resolves_file_manager_virtual_root(monkeypatch, tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    monkeypatch.setattr(routes_shared, "_REPO_ROOT", project_root)
    monkeypatch.setattr(
        routes_file_manager,
        "_discover_file_manager_roots",
        lambda: [
            {
                "id": "/workspace",
                "label": "workspace",
                "path": workspace_dir,
                "kind": "project",
            }
        ],
    )

    resolved = routes_shared._resolve_terminal_start_dir("/workspace")

    assert resolved == workspace_dir


def test_terminal_start_dir_file_manager_mode_resolves_project_relative_absolute_path(monkeypatch, tmp_path: Path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    _set_repo_root(monkeypatch, tmp_path)

    resolved = routes_shared._resolve_terminal_start_dir("/workspace", path_mode="file_manager")

    assert resolved == workspace_dir


def test_active_session_provider_prefers_session_meta(monkeypatch):
    session_agent_store.set_session_agent_meta("session-1", {"provider_id": "claude"})
    monkeypatch.setattr(routes_shared, "get_provider", lambda provider_id: {"id": provider_id, "bin": "claude"})

    provider = routes_shared._active_session_provider("session-1")

    assert provider == {"id": "claude", "bin": "claude"}


def test_verify_active_workflow_session_uses_tracked_session_name(monkeypatch):
    observed: list[str] = []

    monkeypatch.setattr(
        routes,
        "_workflow_execute_status",
        lambda: {
            "thread_alive": True,
            "session_name": "webui-live-1776144071-dd98",
            "status": "waiting_for_continue",
        },
    )
    monkeypatch.setattr(routes, "_tmux_session_exists", lambda session_name: observed.append(session_name) or True)
    monkeypatch.setattr(routes, "_reset_workflow_execute_state", lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not reset workflow state")))

    routes._verify_active_workflow_session()

    assert observed == ["webui-live-1776144071-dd98"]
