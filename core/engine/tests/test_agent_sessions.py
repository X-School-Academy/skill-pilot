import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_sessions


def test_infer_session_category_from_project_paths(tmp_path):
    repo = tmp_path
    (repo / "workspace" / "config").mkdir(parents=True)
    project_req = repo / "workspace" / "vibe-coding" / "local-s3-cloudfront-file-manager" / "requirements.md"
    project_req.parent.mkdir(parents=True)
    project_req.write_text("# requirements\n", encoding="utf-8")
    (repo / "core" / "engine" / "hooks").mkdir(parents=True)
    config_file = repo / "config" / "ai_providers.json5"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("{}", encoding="utf-8")

    assert agent_sessions.infer_session_category("check workspace/config", repo) == "config"
    assert agent_sessions.infer_session_category(f"check {repo}/workspace/config", repo) == "config"
    assert (
        agent_sessions.infer_session_category(
            "@workspace/vibe-coding/local-s3-cloudfront-file-manager/requirements.md",
            repo,
        )
        == "local-s3-cloudfront-file-manager"
    )
    assert agent_sessions.infer_session_category("update core/engine/hooks", repo) == "hooks"
    assert agent_sessions.infer_session_category("read config/ai_providers.json5", repo) == "config"
    assert agent_sessions.infer_session_category("no path here", repo) == "/"


def test_infer_session_category_from_showcase_directory(tmp_path):
    repo = tmp_path / "repo"
    directory = repo / "workspace" / "tasks" / "aws-credentials-s3-cloudfront"
    directory.mkdir(parents=True)

    assert (
        agent_sessions.infer_session_category_from_directory(
            "workspace/tasks/aws-credentials-s3-cloudfront",
            repo,
        )
        == "aws-credentials-s3-cloudfront"
    )
    assert agent_sessions.infer_session_category_from_directory(str(directory), repo) == "aws-credentials-s3-cloudfront"


def test_list_and_render_agent_session_without_commit_block(tmp_path):
    session_dir = tmp_path / "agent-sessions"
    session_dir.mkdir()
    path = session_dir / "20260526T052351Z-codex-session-1.jsonl"
    records = [
        {
            "type": "session_start",
            "timestamp": "20260526T052351Z",
            "agent": "codex",
            "session_id": "session-1",
            "metadata": {"model": "gpt-5.5", "git_commit": "abc123"},
        },
        {
            "type": "session_category",
            "timestamp": "20260526T052352Z",
            "agent": "codex",
            "session_id": "session-1",
            "category": "hooks",
        },
        {
            "type": "user_prompt",
            "timestamp": "20260526T052353Z",
            "agent": "codex",
            "session_id": "session-1",
            "content": "update core/engine/hooks",
        },
        {
            "type": "agent_response",
            "timestamp": "20260526T052400Z",
            "agent": "codex",
            "session_id": "session-1",
            "content": "Done.",
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    categories = agent_sessions.list_agent_session_categories(session_dir)
    assert categories[0]["name"] == "hooks"
    assert categories[0]["sessions"][0]["title"] == "update core/engine/hooks"
    assert categories[0]["sessions"][0]["resume_supported"] is True
    assert categories[0]["sessions"][0]["has_analysis"] is False

    payload = agent_sessions.read_agent_session_payload(path.name, session_dir)
    assert "- agent: codex" in payload["markdown"]
    assert "- model: gpt-5.5" in payload["markdown"]
    assert "- time: 2026-05-26T05:24:00Z" in payload["markdown"]
    assert "## User Prompt" in payload["markdown"]
    assert "## Agent Response" in payload["markdown"]
    assert "git checkout" not in payload["markdown"]
    assert "- commit:" not in payload["markdown"]


def test_agent_session_analysis_file_is_exposed(tmp_path):
    session_dir = tmp_path / "agent-sessions"
    session_dir.mkdir()
    path = session_dir / "20260526T052351Z-codex-session-1.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(record)
            for record in [
                {
                    "type": "session_start",
                    "timestamp": "20260526T052351Z",
                    "agent": "codex",
                    "session_id": "session-1",
                },
                {
                    "type": "user_prompt",
                    "timestamp": "20260526T052353Z",
                    "agent": "codex",
                    "session_id": "session-1",
                    "content": "Build the app",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    analysis_path = session_dir / "20260526T052351Z-codex-session-1_analysis.md"
    analysis_path.write_text("# Analysis\n\nUse better tests.\n", encoding="utf-8")

    categories = agent_sessions.list_agent_session_categories(session_dir)
    assert categories[0]["sessions"][0]["has_analysis"] is True
    assert categories[0]["sessions"][0]["analysis_file"] == analysis_path.name

    payload = agent_sessions.read_agent_session_payload(path.name, session_dir)
    assert payload["analysis_file"] == analysis_path.name
    assert payload["analysis_markdown"] == "# Analysis\n\nUse better tests.\n"
    assert payload["jsonl_path"] == str(path)


def test_agent_session_list_hides_sessions_without_user_prompt(tmp_path):
    session_dir = tmp_path / "agent-sessions"
    session_dir.mkdir()
    (session_dir / "20260526T052351Z-codex-empty.jsonl").write_text(
        json.dumps(
            {
                "type": "session_start",
                "timestamp": "20260526T052351Z",
                "agent": "codex",
                "session_id": "empty-session",
                "metadata": {"model": "gpt-5.5"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert agent_sessions.list_agent_session_categories(session_dir) == []
