import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import llm_service


TEXT_INPUT = "my new password `abracadabra` should be updated and I should be logged in automatically"


def test_llm_get_text():
    result = llm_service.llm_get_text(
        [
            {
                "role": "user",
                "content": (
                    f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                    "Then reply with exactly this prefix and the number only once: "
                    "'The total number of a is:'"
                ),
            }
        ],
    )
    print(f"llm_get_text raw output:\n{result}")

    assert "The total number of a is:" in result


def test_llm_get_json():
    result = llm_service.llm_get_json(
        [
            {
                "role": "user",
                "content": (
                    f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                    'Return JSON only in this shape: {"input":"...","count":number,"message":"The total number of a is: N"}'
                ),
            }
        ]
    )
    print(f"llm_get_json raw output:\n{result}")

    assert isinstance(result.get("count"), int)
    assert isinstance(result.get("input"), str)
    assert result["input"] == TEXT_INPUT
    assert isinstance(result.get("message"), str)
    assert result["message"].startswith("The total number of a is:")


def test_llm_stream():
    chunks = list(
        llm_service.llm_stream(
            (
                f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                "Then reply with exactly this prefix and the number only once: "
                "'The total number of a is:'"
            )
        )
    )

    assert chunks[-1] == b"[-DONE-]"
    streamed_text = b"".join(chunk for chunk in chunks if chunk not in {b"[-DONE-]", b"[-ERROR-]"}).decode(
        "utf-8",
        errors="replace",
    )
    print(f"llm_stream raw output:\n{streamed_text}")
    assert "The total number of a is:" in streamed_text


def test_parse_stream_json_text_claude_assistant_message():
    provider = {"bin": "claude", "args": ["--output-format=stream-json"]}
    sample = "\n".join(
        [
            json.dumps(
                {
                    "type": "system",
                    "subtype": "init",
                    "cwd": "/tmp",
                    "session_id": "session-1",
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "text",
                                "text": '{"scenes":[{"scene_type":"text_only","text":"hello","voice_over":"hi"}]}',
                            }
                        ]
                    },
                }
            ),
            json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done"}),
        ]
    )

    parsed = llm_service._parse_stream_json_text(provider, sample)

    assert parsed == '{"scenes":[{"scene_type":"text_only","text":"hello","voice_over":"hi"}]}'
    assert llm_service._extract_json_payload(parsed)["scenes"][0]["scene_type"] == "text_only"


def test_resolve_arg_expands_env_placeholders(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_BASE_URL", "https://example.test/v1")

    resolved = llm_service._resolve_arg('model_providers.skill_pilot.base_url="${OPENAI_COMPAT_BASE_URL}"')

    assert resolved == 'model_providers.skill_pilot.base_url="https://example.test/v1"'


def test_build_terminal_command_reuses_codex_provider_args():
    provider = {
        "bin": "codex",
        "model": "model-name",
        "args": [
            "exec",
            "-c",
            'model_providers.skill_pilot.name="skill_pilot"',
            "-c",
            'model_providers.skill_pilot.base_url="https://example.test/v1"',
            "-c",
            'model_provider="skill_pilot"',
            "--json",
            "{{prompt}}",
        ],
    }

    command = llm_service.build_terminal_command(provider, "interactive prompt")

    assert command == [
        "codex",
        "--model",
        "model-name",
        "-c",
        'model_providers.skill_pilot.name="skill_pilot"',
        "-c",
        'model_providers.skill_pilot.base_url="https://example.test/v1"',
        "-c",
        'model_provider="skill_pilot"',
        "interactive prompt",
    ]


def test_background_llm_selects_skill_pilot_when_configured(monkeypatch):
    config = {
        "default": {"llm": "claude", "background_llm": "skill-pilot"},
        "llm": [
            {"id": "claude", "bin": "claude", "args": ["{{prompt}}"]},
            {
                "id": "skill-pilot",
                "bin": "core/bin/skill-pilot-agent",
                "background_only": True,
                "args": ["--model", "${SKILL_PILOT_MODEL}", "{{prompt}}"],
            },
        ],
    }
    monkeypatch.setattr(llm_service, "load_provider_config", lambda: config)
    monkeypatch.setenv("SKILL_PILOT_MODEL", "skill-pilot-mini")

    provider = llm_service.get_background_provider(None)
    command = llm_service.build_llm_command(provider, "hello")

    assert provider["id"] == "skill-pilot"
    assert command == [
        "core/bin/skill-pilot-agent",
        "--model",
        "skill-pilot-mini",
        "hello",
    ]


def test_background_llm_falls_back_when_not_configured(monkeypatch):
    config = {
        "default": {"llm": "claude", "background_llm": ""},
        "llm": [
            {"id": "claude", "bin": "claude", "args": ["{{prompt}}"]},
            {
                "id": "skill-pilot",
                "bin": "core/bin/skill-pilot-agent",
                "background-only": True,
                "args": ["{{prompt}}"],
            },
        ],
    }
    monkeypatch.setattr(llm_service, "load_provider_config", lambda: config)

    provider = llm_service.get_background_provider(None)

    assert provider["id"] == "claude"
    assert [p["id"] for p in llm_service.load_llm_providers()] == ["claude"]


def test_explicit_provider_does_not_select_background_only_provider(monkeypatch):
    config = {
        "default": {"llm": "claude", "background_llm": "skill-pilot"},
        "llm": [
            {"id": "claude", "bin": "claude", "args": ["{{prompt}}"]},
            {
                "id": "skill-pilot",
                "bin": "core/bin/skill-pilot-agent",
                "background-only": True,
                "args": ["{{prompt}}"],
            },
        ],
    }
    monkeypatch.setattr(llm_service, "load_provider_config", lambda: config)

    provider = llm_service.get_provider("skill-pilot")

    assert provider["id"] == "claude"


def test_skill_pilot_provider_env_expands(monkeypatch):
    provider = {
        "env": {
            "SKILL_PILOT_BASE_URL": "${SKILL_PILOT_BASE_URL}",
            "SKILL_PILOT_API_KEY": "${SKILL_PILOT_API_KEY}",
            "SKILL_PILOT_MODEL": "${SKILL_PILOT_MODEL}",
        }
    }
    monkeypatch.setenv("SKILL_PILOT_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("SKILL_PILOT_API_KEY", "test-key")
    monkeypatch.setenv("SKILL_PILOT_MODEL", "skill-pilot-mini")

    env = llm_service._resolve_provider_env(provider)

    assert env == {
        "SKILL_PILOT_BASE_URL": "http://127.0.0.1:8000/v1",
        "SKILL_PILOT_API_KEY": "test-key",
        "SKILL_PILOT_MODEL": "skill-pilot-mini",
    }
