import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from mcp_servers.mcp_to_skills import cli
from mcp_servers.mcp_to_skills.cli import EngineNotStartedError, build_parser
from mcp_servers.mcp_to_skills.service import Bridge
from mcp_servers.mcp_to_skills.sync import load_mcp_configs


def test_create_audio_parser_accepts_text_format_and_voice():
    args = build_parser().parse_args(["create-audio", "--text", "hello", "--format", "wav", "--voice", "alloy"])

    assert args.command == "create-audio"
    assert args.text == "hello"
    assert args.format == "wav"
    assert args.voice == "alloy"


def test_agent_cli_parser_accepts_prompt_and_flags():
    args = build_parser().parse_args(["agent-cli", "--provider", "openai", "--no-network", "hello"])

    assert args.command == "agent-cli"
    assert args.provider == "openai"
    assert args.network is False
    assert args.prompt == ["hello"]


def test_runtime_fallback_error_includes_socket_attempt_details(monkeypatch):
    prod_socket = Path("/tmp/engine.sock")
    dev_socket = Path("/tmp/engine-dev.sock")

    def fake_send_request(_json_str, socket_path, _timeout):
        raise ConnectionRefusedError(f"cannot connect to {socket_path.name}")

    monkeypatch.delenv("SKILL_PILOT_RUNTIME_MODE", raising=False)
    monkeypatch.setattr(cli, "default_socket_candidates", lambda: [prod_socket, dev_socket])
    monkeypatch.setattr(cli, "send_request", fake_send_request)

    with pytest.raises(EngineNotStartedError) as exc_info:
        cli.send_request_with_runtime_fallback(
            "{}",
            timeout=0.01,
            explicit_socket=False,
        )

    message = str(exc_info.value)
    assert "your Skill Pilot Engine (Prod or Dev) is not started" in message
    assert str(prod_socket) in message
    assert str(dev_socket) in message
    assert "ConnectionRefusedError" in message


def test_runtime_fallback_error_respects_dev_mode_in_diagnostics(tmp_path, monkeypatch):
    dev_socket = tmp_path / "engine-dev.sock"
    monkeypatch.setenv("SKILL_PILOT_RUNTIME_MODE", "development")
    monkeypatch.setattr(cli, "default_socket_candidates", lambda: [dev_socket])

    with pytest.raises(EngineNotStartedError) as exc_info:
        cli.send_request_with_runtime_fallback(
            "{}",
            timeout=0.01,
            explicit_socket=False,
        )

    message = str(exc_info.value)
    assert "your Skill Pilot Engine (Dev) is not started" in message
    assert str(dev_socket) in message
    assert "Socket connection attempts failed" in message


def test_create_audio_operation_dispatches_to_audio_creator(monkeypatch):
    calls = []

    def fake_create_audio(self, text: str, output_format: str, voice: str | None = None) -> dict[str, str]:
        calls.append((text, output_format, voice))
        return {"path": "/tmp/test.wav", "provider": "skill-pilot", "format": output_format, "voice": voice or ""}

    monkeypatch.setattr(Bridge, "_create_audio", fake_create_audio)
    bridge = Bridge.__new__(Bridge)

    result = bridge.handle_request({"operation": "create_audio", "text": "hello", "format": "wav", "voice": "alloy"})

    assert result == {
        "status": "ok",
        "result": {"path": "/tmp/test.wav", "provider": "skill-pilot", "format": "wav", "voice": "alloy"},
    }
    assert calls == [("hello", "wav", "alloy")]


def test_mcp_env_optional_empty_values_are_removed(tmp_path, monkeypatch):
    config_path = tmp_path / "mcp.json5"
    config_path.write_text(
        """
        {
          mcpServers: {
            demo: {
              command: "demo",
              env: {
                EMPTY_OPTIONAL: "${EMPTY_OPTIONAL:-}",
                MISSING_OPTIONAL: "${MISSING_OPTIONAL:-}",
                PRESENT_OPTIONAL: "${PRESENT_OPTIONAL:-}",
                DEFAULTED_OPTIONAL: "${DEFAULTED_OPTIONAL:-fallback}",
              },
            },
          },
        }
        """
    )
    monkeypatch.setenv("EMPTY_OPTIONAL", "")
    monkeypatch.setenv("PRESENT_OPTIONAL", "present")
    monkeypatch.delenv("MISSING_OPTIONAL", raising=False)
    monkeypatch.delenv("DEFAULTED_OPTIONAL", raising=False)

    servers, missing_env = load_mcp_configs(config_path)

    assert missing_env == {}
    assert servers["demo"].env == {
        "PRESENT_OPTIONAL": "present",
        "DEFAULTED_OPTIONAL": "fallback",
    }
