import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes_shared
from mcp_servers.mcp_to_skills import cli
from mcp_servers.mcp_to_skills.workflow_execution import build_node_prompt, load_workflow_graph
from workflow_editor_utils import validate_workflow_doc


def _workflow_doc_with_subagent() -> dict:
    return {
        "version": "1.0",
        "name": "subagent-workflow",
        "updated_at": "2026-05-23T00:00:00Z",
        "nodes": [
            {"id": 0, "type": "start", "position": {"x": 0, "y": 0}},
            {
                "id": 1,
                "type": "agent",
                "position": {"x": 100, "y": 0},
                "data": {
                    "title": "Review",
                    "provider_id": "codex",
                    "subagent": "code-reviewer",
                    "responsibility": "",
                },
            },
            {"id": -1, "type": "end", "position": {"x": 200, "y": 0}},
        ],
        "edges": [
            {"id": "0->1", "source": 0, "target": 1},
            {"id": "1->-1", "source": 1, "target": -1},
        ],
    }


def test_validate_workflow_doc_accepts_subagent_field():
    assert validate_workflow_doc(_workflow_doc_with_subagent()) == []


def test_validate_workflow_doc_requires_subagent_or_responsibility():
    doc = _workflow_doc_with_subagent()
    doc["nodes"][1]["data"]["subagent"] = ""

    errors = validate_workflow_doc(doc)

    assert any(error["rule"] == "AGENT_FIELD" for error in errors)
    assert any("`subagent` or `responsibility`" in error["message"] for error in errors)


def test_build_node_prompt_uses_subagent_instruction(tmp_path: Path):
    workflow_dir = tmp_path / "core" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_file = workflow_dir / "subagent-workflow.json"
    workflow_file.write_text(json.dumps(_workflow_doc_with_subagent()), encoding="utf-8")

    graph = load_workflow_graph(workflow_file, workflow_dir)
    prompt = build_node_prompt(
        graph=graph,
        current_node=graph.id_to_node[1],
        workflow_prompt="Review this change",
        output_root=tmp_path / ".skillpilot" / "temp" / "workflow",
        upstream_node_ids=[],
    )

    assert "Skill Pilot subagent" in prompt
    assert "- Subagent: code-reviewer" in prompt
    assert "- Use Skill Pilot subagent: code-reviewer." in prompt
    assert "agent skill" not in prompt


def test_resolve_run_workflow_inputs_supports_named_and_none_tmux():
    args = argparse.Namespace(
        workflow="sample",
        workflow_opt=None,
        prompt=["hello", "world"],
        prompt_opt=None,
        tmux_session="none",
    )

    workflow, prompt, tmux_session = cli._resolve_run_workflow_inputs(args)

    assert workflow == "sample"
    assert prompt == "hello world"
    assert tmux_session is None


def test_resolve_run_workflow_inputs_rejects_conflicting_prompt_values():
    args = argparse.Namespace(
        workflow="sample",
        workflow_opt=None,
        prompt=["one"],
        prompt_opt="two",
        tmux_session=None,
    )

    try:
        cli._resolve_run_workflow_inputs(args)
    except ValueError as exc:
        assert "positional and --prompt must match" in str(exc)
    else:
        raise AssertionError("expected ValueError for conflicting prompt sources")


def test_run_workflow_rejects_tmux_only_flags_without_tmux_session(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["tool-cli", "run-workflow", "--workflow=test.json", "--prompt=test", "--resume"],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--resume and --auto-continue require --tmux-session" in captured.err


def test_run_workflow_tmux_mode_starts_terminal_monitor(monkeypatch, capsys):
    observed: dict[str, object] = {}

    def fake_send_request(json_str: str, timeout: float, socket_path: Path, explicit_socket: bool, socket_candidates=None) -> str:
        del timeout, socket_path, explicit_socket, socket_candidates
        observed.update(json.loads(json_str))
        return json.dumps(
            {
                "status": "ok",
                "result": {
                    "startup": {
                        "prompt": "You are running as an AI agent node inside a multi-step workflow."
                    }
                },
            }
        )

    monkeypatch.setattr(cli, "send_request_with_runtime_fallback", fake_send_request)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tool-cli",
            "run-workflow",
            "--workflow=core/workflows/test.json",
            "--prompt=Run this workflow",
            "--tmux-session=my-session",
            "--resume",
            "--auto-continue",
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert observed["operation"] == "start_workflow_terminal"
    assert observed["workflow"] == "core/workflows/test.json"
    assert observed["prompt"] == "Run this workflow"
    assert observed["tmux_session"] == "my-session"
    assert observed["resume"] is True
    assert observed["next_node_trigger"] == "auto_continue"
    assert "You are running as an AI agent node inside a multi-step workflow." in captured.out


def test_run_workflow_positional_mode_preserves_legacy_execution(monkeypatch, capsys, tmp_path: Path):
    class FakeResult:
        status = "ok"
        workflow = "core/workflows/sample.json"
        workflow_name = "sample"
        duration_sec = 0.1
        run_id = "run-1"
        output_root = str(tmp_path / "output")
        node_status = {1: "done"}
        final_outputs = []
        errors = []

    monkeypatch.setattr(cli, "resolve_workflow_file", lambda workflow_arg, workflows_root: workflows_root / workflow_arg)
    monkeypatch.setattr(cli, "run_workflow", lambda **kwargs: FakeResult())
    monkeypatch.setattr(sys, "argv", ["tool-cli", "run-workflow", "sample.json", "Legacy prompt"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ok"' in captured.out
    assert '"workflow_name": "sample"' in captured.out


def test_build_provider_command_includes_tmux_and_workflow_env(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(routes_shared, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(routes_shared, "get_provider", lambda provider_id: {"id": provider_id, "bin": "codex"})
    monkeypatch.setattr(routes_shared, "build_terminal_command", lambda provider, prompt, auto_allow, network_allow, sandbox_mode: ["codex", prompt])
    monkeypatch.setattr(routes_shared, "_resolve_provider_env", lambda provider: {"OPENAI_BASE_URL": "http://example.test"})

    routes_shared._build_provider_command(
        provider_id="codex",
        prompt="test prompt",
        sandbox=True,
        auto=False,
        network=True,
        extra_env={
            "TMUX_SESSION_NAME": "session-1",
            "SKILL_PILOT_WORKFLOW_NODE": "1",
            "SKILL_PILOT_WORKFLOW_RUN_ID": "run-1",
        },
    )

    payload_files = list((tmp_path / ".skillpilot" / "temp" / "tmux-argv").glob("*.json"))
    assert len(payload_files) == 1
    payload = json.loads(payload_files[0].read_text(encoding="utf-8"))
    assert payload["env"]["TMUX_SESSION_NAME"] == "session-1"
    assert payload["env"]["SKILL_PILOT_WORKFLOW_NODE"] == "1"
    assert payload["env"]["SKILL_PILOT_WORKFLOW_RUN_ID"] == "run-1"
    assert payload["env"]["OPENAI_BASE_URL"] == "http://example.test"
