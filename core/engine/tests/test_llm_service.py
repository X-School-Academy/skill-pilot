import sys
from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import image_service
import llm_service
import tts_service


TEXT_INPUT = "my new password `abracadabra` should be updated and I should be logged in automatically"
TEMP_OUTPUT_DIR = Path(__file__).resolve().parents[3] / ".skillpilot" / "temp"


def _copy_generated_file(source: str, target_name: str) -> Path:
    source_path = Path(source)
    assert source_path.is_file()
    assert source_path.stat().st_size > 0

    TEMP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = TEMP_OUTPUT_DIR / target_name
    shutil.copyfile(source_path, target)

    assert target.is_file()
    assert target.stat().st_size > 0
    return target


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


def test_llm_get_text_ignores_stderr_logs_on_success():
    provider = {"id": "skill-pilot", "bin": "skill-pilot-agent", "args": ["{{prompt}}"]}
    completed = MagicMock(
        returncode=0,
        stdout="flowchart LR\n    A --> B\n",
        stderr="[18/May/2026:08:19:41 +1000] INFO noisy runtime log\n",
    )

    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ):
        result = llm_service.llm_get_text([{"role": "user", "content": "Return Mermaid code"}])

    assert result == "flowchart LR\n    A --> B"
    assert "18/May/2026" not in result


def test_llm_get_text_raises_on_nonzero_even_with_stdout():
    provider = {"id": "skill-pilot", "bin": "skill-pilot-agent", "args": ["{{prompt}}"]}
    completed = MagicMock(
        returncode=1,
        stdout="flowchart LR\n    A --> B\n",
        stderr="skill-pilot-agent error: failed\n",
    )

    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ):
        try:
            llm_service.llm_get_text([{"role": "user", "content": "Return Mermaid code"}])
        except RuntimeError as exc:
            assert "LLM command failed" in str(exc)
            assert "skill-pilot-agent error: failed" in str(exc)
        else:
            raise AssertionError("Expected llm_get_text to raise on non-zero provider exit")


def test_llm_get_text_passes_cli_session_env_and_uses_gemini_resume(monkeypatch, tmp_path):
    provider = {"id": "gemini", "bin": "gemini", "args": ["--output-format", "stream-json", "-p", "{{prompt}}"]}
    cli_session_path = tmp_path / "cli-sessions" / "workflow-abc.jsonl"
    cli_session_path.parent.mkdir(parents=True)
    cli_session_path.write_text(
        '{"type":"session_start","agent":"gemini","session_id":"gemini-session-123"}\n',
        encoding="utf-8",
    )
    completed = MagicMock(returncode=0, stdout='{"type":"message","role":"assistant","content":"ok"}\n', stderr="")

    monkeypatch.setattr(llm_service, "CLI_SESSION_DIR", tmp_path / "cli-sessions")
    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "Next"}],
            cli_session_id="workflow-abc",
        )

    assert result == "ok"
    cmd = run_mock.call_args.args[0]
    assert cmd == [
        "gemini",
        "--output-format",
        "stream-json",
        "-p",
        "USER:\nNext",
        "--resume",
        "gemini-session-123",
    ]
    assert run_mock.call_args.kwargs["env"]["LLM_CLI_SESSION_ID"] == "workflow-abc"


def test_llm_get_text_starts_new_cli_session_when_no_record(monkeypatch, tmp_path):
    provider = {"id": "gemini", "bin": "gemini", "args": ["--output-format", "stream-json", "-p", "{{prompt}}"]}
    completed = MagicMock(
        returncode=0,
        stdout=(
            '{"type":"session.started","session_id":"gemini-session-123"}\n'
            '{"type":"message","role":"assistant","content":"ok"}\n'
        ),
        stderr="",
    )

    monkeypatch.setattr(llm_service, "CLI_SESSION_DIR", tmp_path / "cli-sessions")
    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "First"}],
            cli_session_id="workflow-new",
        )

    assert result == "ok"
    cmd = run_mock.call_args.args[0]
    assert cmd == ["gemini", "--output-format", "stream-json", "-p", "USER:\nFirst"]
    assert run_mock.call_args.kwargs["env"]["LLM_CLI_SESSION_ID"] == "workflow-new"
    records = (tmp_path / "cli-sessions" / "workflow-new.jsonl").read_text(encoding="utf-8")
    assert '"session_id":"gemini-session-123"' in records
    assert '"type":"user_prompt"' in records
    assert '"type":"agent_response"' in records


def test_llm_get_text_passes_cwd_to_subprocess(tmp_path):
    provider = {"id": "skill-pilot", "bin": "skill-pilot-agent", "args": ["{{prompt}}"]}
    completed = MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "First"}],
            cwd=tmp_path,
        )

    assert result == "ok"
    assert run_mock.call_args.kwargs["cwd"] == str(tmp_path)


def test_llm_get_text_defaults_cwd_to_project_root():
    provider = {"id": "skill-pilot", "bin": "skill-pilot-agent", "args": ["{{prompt}}"]}
    completed = MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = llm_service.llm_get_text([{"role": "user", "content": "First"}])

    assert result == "ok"
    assert run_mock.call_args.kwargs["cwd"] == str(llm_service.PROJECT_DIR)
    assert run_mock.call_args.kwargs["stdin"] == llm_service.subprocess.DEVNULL


def test_llm_get_text_appends_turns_for_existing_cli_session(monkeypatch, tmp_path):
    provider = {"id": "gemini", "bin": "gemini", "args": ["--output-format", "stream-json", "-p", "{{prompt}}"]}
    cli_session_path = tmp_path / "cli-sessions" / "workflow-existing.jsonl"
    cli_session_path.parent.mkdir(parents=True)
    cli_session_path.write_text(
        '{"type":"session_start","agent":"gemini","session_id":"gemini-session-123"}\n',
        encoding="utf-8",
    )
    completed = MagicMock(
        returncode=0,
        stdout=(
            '{"type":"init","session_id":"gemini-session-123"}\n'
            '{"type":"message","role":"assistant","content":"again"}\n'
        ),
        stderr="",
    )

    monkeypatch.setattr(llm_service, "CLI_SESSION_DIR", tmp_path / "cli-sessions")
    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ):
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "Again"}],
            cli_session_id="workflow-existing",
        )

    assert result == "again"
    records = (tmp_path / "cli-sessions" / "workflow-existing.jsonl").read_text(encoding="utf-8")
    assert records.count('"type":"session_start"') == 1
    assert '"content":"USER:\\nAgain"' in records
    assert '"content":"again"' in records


def test_llm_get_text_dedupes_fallback_when_hooks_recorded_turn(monkeypatch, tmp_path):
    provider = {"id": "codex", "bin": "codex", "args": ["exec", "--json", "{{prompt}}"]}
    cli_session_path = tmp_path / "cli-sessions" / "workflow-hooked.jsonl"
    cli_session_path.parent.mkdir(parents=True)
    cli_session_path.write_text(
        "\n".join(
            [
                '{"type":"session_start","agent":"codex","session_id":"codex-session-123"}',
                '{"type":"user_prompt","agent":"codex","session_id":"codex-session-123","content":"USER:\\nFirst"}',
                '{"type":"agent_response","agent":"codex","session_id":"codex-session-123","content":"ok"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    completed = MagicMock(
        returncode=0,
        stdout=(
            '{"type":"thread.started","thread_id":"codex-session-123"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n'
        ),
        stderr="",
    )

    monkeypatch.setattr(llm_service, "CLI_SESSION_DIR", tmp_path / "cli-sessions")
    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ):
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "First"}],
            cli_session_id="workflow-hooked",
        )

    assert result == "ok"
    records = cli_session_path.read_text(encoding="utf-8")
    assert records.count('"type":"session_start"') == 1
    assert records.count('"type":"user_prompt"') == 1
    assert records.count('"type":"agent_response"') == 1


def test_build_llm_resume_command_supports_agent_cli_providers():
    assert llm_service.build_llm_resume_command(
        {"bin": "claude", "args": ["--print", "--output-format=stream-json", "{{prompt}}"]},
        "USER:\nNext",
        "claude-session",
    ) == ["claude", "--print", "--output-format=stream-json", "--resume", "claude-session", "USER:\nNext"]

    assert llm_service.build_llm_resume_command(
        {"bin": "gemini", "args": ["--prompt", "{{prompt}}", "--output-format", "stream-json"]},
        "USER:\nNext",
        "gemini-session",
    ) == ["gemini", "--prompt", "USER:\nNext", "--output-format", "stream-json", "--resume", "gemini-session"]

    assert llm_service.build_llm_resume_command(
        {"bin": "opencode", "args": ["run", "--format", "json", "{{prompt}}"]},
        "USER:\nNext",
        "opencode-session",
    ) == ["opencode", "run", "--session", "opencode-session", "--format", "json", "USER:\nNext"]


def test_resume_command_preserves_configured_args_model_and_output_format():
    prompt = "USER:\nNext"
    provider = {
        "id": "codex-compat",
        "bin": "codex",
        "model": "skill-pilot",
        "sandbox-args": ["--sandbox", "workspace-write"],
        "args": [
            "exec",
            "-c",
            'model_providers.skill_pilot.name="skill_pilot"',
            "-c",
            'model_provider="skill_pilot"',
            "--json",
            "{{prompt}}",
        ],
    }

    base_cmd = llm_service.build_llm_command(provider, prompt)
    resume_cmd = llm_service.build_llm_resume_command(provider, prompt, "codex-session")

    assert base_cmd == [
        "codex",
        "--sandbox",
        "workspace-write",
        "--model",
        "skill-pilot",
        "exec",
        "-c",
        'model_providers.skill_pilot.name="skill_pilot"',
        "-c",
        'model_provider="skill_pilot"',
        "--json",
        prompt,
    ]
    assert resume_cmd == [
        "codex",
        "--sandbox",
        "workspace-write",
        "--model",
        "skill-pilot",
        "exec",
        "resume",
        "-c",
        'model_providers.skill_pilot.name="skill_pilot"',
        "-c",
        'model_provider="skill_pilot"',
        "--json",
        "codex-session",
        prompt,
    ]


def test_llm_get_text_preserves_provider_env_and_adds_cli_session_env(monkeypatch, tmp_path):
    provider = {
        "id": "codex",
        "bin": "codex",
        "args": ["exec", "--json", "{{prompt}}"],
        "env": {
            "OPENAI_COMPAT_API_KEY": "${TEST_COMPAT_KEY}",
            "EMPTY_ALLOWED": "",
        },
    }
    completed = MagicMock(
        returncode=0,
        stdout=(
            '{"type":"thread.started","thread_id":"codex-session"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}\n'
        ),
        stderr="",
    )

    monkeypatch.setenv("TEST_COMPAT_KEY", "secret-value")
    monkeypatch.setattr(llm_service, "CLI_SESSION_DIR", tmp_path / "cli-sessions")
    with patch("llm_service.get_background_provider", return_value=provider), patch(
        "llm_service.subprocess.run",
        return_value=completed,
    ) as run_mock:
        result = llm_service.llm_get_text(
            [{"role": "user", "content": "First"}],
            cli_session_id="workflow-env",
        )

    assert result == "ok"
    env = run_mock.call_args.kwargs["env"]
    assert env["OPENAI_COMPAT_API_KEY"] == "secret-value"
    assert env["EMPTY_ALLOWED"] == ""
    assert env["LLM_CLI_SESSION_ID"] == "workflow-env"


def test_parse_claude_stream_prefers_final_result_over_duplicate_deltas():
    provider = {"id": "claude", "bin": "claude", "args": ["--output-format=stream-json"]}
    output = "\n".join(
        [
            '{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"O"}}}',
            '{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"K"}}}',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"OK"}]}}',
            '{"type":"result","result":"OK"}',
        ]
    )

    assert llm_service._parse_stream_json_text(provider, output) == "OK"


def test_extract_claude_session_id_prefers_result_over_hook_session():
    provider = {"id": "claude", "bin": "claude"}
    output = "\n".join(
        [
            '{"type":"system","subtype":"hook_started","session_id":"hook-session"}',
            '{"type":"system","subtype":"init","session_id":"real-session"}',
            '{"type":"result","session_id":"real-session","result":"OK"}',
        ]
    )

    assert llm_service._extract_cli_output_session_id(provider, output) == "real-session"


def test_parse_opencode_json_text_events():
    provider = {"id": "opencode", "bin": "opencode", "args": ["--format", "json"]}
    output = "\n".join(
        [
            '{"type":"step_start","sessionID":"ses_123"}',
            '{"type":"text","sessionID":"ses_123","part":{"type":"text","text":"ONE"}}',
            '{"type":"step_finish","sessionID":"ses_123"}',
        ]
    )

    assert llm_service._parse_stream_json_text(provider, output) == "ONE"


def test_llm_get_tts():
    result = tts_service.text_to_speech_file(
        "Skill Pilot test audio. Count the letter a in abracadabra.",
    )
    output_path = _copy_generated_file(result, f"test_llm_get_tts{Path(result).suffix or '.wav'}")
    print(f"tts audio output: {output_path}")

    assert output_path.suffix.lower() in {".mp3", ".wav", ".opus", ".aac", ".flac"}


def test_llm_get_image():
    result = image_service.generate_image_file(
        "A simple clean test image of the word Skill Pilot on a white card.",
        size="1024x1024",
    )
    output_path = _copy_generated_file(result, f"test_llm_get_image{Path(result).suffix or '.png'}")
    print(f"image output: {output_path}")

    assert output_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


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
