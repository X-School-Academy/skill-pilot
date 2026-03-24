import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from mcp_servers.media.script_executor import ScriptExecutor


def test_normalize_input_reference_preserves_remote_comfy_path():
    remote_path = "/home/ubuntu/workspace/ComfyUI/input/reference.mp3"
    executor = ScriptExecutor()

    assert executor._normalize_input_reference(remote_path, "Reference voice") == remote_path


def test_normalize_input_reference_preserves_local_absolute_paths(tmp_path):
    local_file = tmp_path / "reference.mp3"
    local_file.write_bytes(b"fake-audio")

    executor = ScriptExecutor()

    assert executor._normalize_input_reference(str(local_file), "Reference voice") == str(local_file)


def test_normalize_input_reference_expands_user_home(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp/skillpilot-home")

    executor = ScriptExecutor()

    assert (
        executor._normalize_input_reference("~/reference.mp3", "Reference voice")
        == "/tmp/skillpilot-home/reference.mp3"
    )
