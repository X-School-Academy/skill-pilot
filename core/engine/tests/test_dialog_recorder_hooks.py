import importlib
import json
from datetime import UTC, datetime
from pathlib import Path


def load_recorder(monkeypatch, tmp_path):
    engine_path = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(engine_path))
    module = importlib.import_module("hooks.dialog_recorder")
    monkeypatch.setattr(module, "SESSION_DIR", tmp_path / "agent-sessions")
    monkeypatch.setattr(module, "utc_now", lambda: datetime(2026, 4, 30, 6, 11, 13, tzinfo=UTC))
    return module


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_session_start_creates_expected_file_and_first_record(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)
    payload = {
        "session_id": "abc-123",
        "hook_event_name": "SessionStart",
        "cwd": "/repo",
        "model": "gpt-5.5",
        "source": "startup",
    }

    path = recorder.session_file("codex", "abc-123", payload)
    recorder.append_record(
        path,
        {
            "type": "session_start",
            "timestamp": recorder.format_timestamp(),
            "agent": "codex",
            "session_id": "abc-123",
            "metadata": recorder.base_metadata(payload),
        },
    )

    assert path.name == "20260430T061113Z-codex-abc-123.jsonl"
    records = read_jsonl(path)
    assert records[0]["type"] == "session_start"
    assert records[0]["metadata"]["source"] == "startup"


def test_prompt_and_response_extract_visible_text_only(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)

    assert recorder.extract_user_prompt({"prompt": "Build the hooks"}) == "Build the hooks"
    assert recorder.extract_agent_response({"last_assistant_message": "Done."}) == "Done."
    assert (
        recorder.extract_agent_response(
            {
                "llm_response": {
                    "candidates": [
                        {"content": {"role": "model", "parts": ["Visible answer"]}},
                    ]
                }
            }
        )
        == "Visible answer"
    )
    assert recorder.text_from_content({"type": "tool_use", "name": "write_file"}) is None


def test_non_start_event_infers_session_start_first(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)
    payload = {
        "session_id": "gem-session",
        "hook_event_name": "BeforeAgent",
        "prompt": "Question?",
        "cwd": "/repo",
    }
    path = recorder.session_file("gemini", "gem-session", payload)

    recorder.ensure_start_record(path, "gemini", "gem-session", payload)
    recorder.append_record(
        path,
        {
            "type": "user_prompt",
            "timestamp": recorder.format_timestamp(),
            "agent": "gemini",
            "session_id": "gem-session",
            "content": recorder.extract_user_prompt(payload),
            "metadata": recorder.base_metadata(payload),
        },
    )

    records = read_jsonl(path)
    assert [record["type"] for record in records] == ["session_start", "user_prompt"]
    assert records[0]["inferred"] is True
    assert records[1]["content"] == "Question?"


def test_opencode_sessionless_events_are_ignored(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)

    assert recorder.opencode_has_session({"event": {"type": "server.instance.disposed"}}) is False
    assert (
        recorder.opencode_has_session(
            {"event": {"type": "session.status", "properties": {"sessionID": "ses_debug"}}}
        )
        is True
    )


def test_opencode_dialog_classification_skips_reasoning(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)

    assert recorder.extract_opencode_dialog(
        {
            "event": {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "type": "text",
                        "text": "hi",
                        "messageID": "msg_user",
                        "sessionID": "ses_debug",
                    }
                },
            }
        }
    ) == ("user_prompt", "hi")
    assert recorder.extract_opencode_dialog(
        {
            "event": {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "type": "text",
                        "text": "Hi",
                        "messageID": "msg_agent",
                        "sessionID": "ses_debug",
                        "time": {"start": 1, "end": 2},
                    }
                },
            }
        }
    ) == ("agent_response", "Hi")
    assert (
        recorder.extract_opencode_dialog(
            {
                "event": {
                    "type": "message.part.updated",
                    "properties": {
                        "part": {
                            "type": "reasoning",
                            "text": "Hidden reasoning",
                            "messageID": "msg_agent",
                            "sessionID": "ses_debug",
                            "time": {"start": 1, "end": 2},
                        }
                    },
                }
            }
        )
        is None
    )


def test_has_record_type_prevents_duplicate_session_end(monkeypatch, tmp_path):
    recorder = load_recorder(monkeypatch, tmp_path)
    path = tmp_path / "agent-sessions" / "20260430T061113Z-gemini-session.jsonl"

    recorder.append_record(
        path,
        {
            "type": "session_start",
            "timestamp": recorder.format_timestamp(),
            "agent": "gemini",
            "session_id": "session",
            "metadata": {},
        },
    )
    recorder.append_record(
        path,
        {
            "type": "session_end",
            "timestamp": recorder.format_timestamp(),
            "agent": "gemini",
            "session_id": "session",
            "metadata": {"reason": "exit"},
        },
    )

    assert recorder.has_record_type(path, "session_end") is True
    records = read_jsonl(path)
    if not recorder.has_record_type(path, "session_end"):
        recorder.append_record(path, {"type": "session_end"})
    assert read_jsonl(path) == records
