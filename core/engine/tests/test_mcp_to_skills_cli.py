import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_servers.mcp_to_skills.cli import build_parser
from mcp_servers.mcp_to_skills.service import Bridge


def test_create_audio_parser_accepts_text_format_and_voice():
    args = build_parser().parse_args(["create-audio", "--text", "hello", "--format", "wav", "--voice", "alloy"])

    assert args.command == "create-audio"
    assert args.text == "hello"
    assert args.format == "wav"
    assert args.voice == "alloy"


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
