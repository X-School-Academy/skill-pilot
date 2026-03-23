import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REF_VOICE = REPO_ROOT / "assets/skillpilot-song.mp3"


def _run_media_tool(tool_name: str, arguments: dict) -> dict:
    request = {
        "server_id": "media",
        "tool_name": tool_name,
        "arguments": arguments,
    }
    result = subprocess.run(
        ["core/bin/tool-cli", "request", json.dumps(request)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    print("--- stdout ---")
    print(result.stdout)
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr)

    assert result.returncode == 0, f"tool-cli failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "No output returned from tool-cli"

    response = json.loads(output)
    assert response, "Empty response from tool"
    return response


def _assert_media_response_has_output(response: dict, suffixes: tuple[str, ...]) -> None:
    response_str = json.dumps(response)
    assert any(suffix in response_str for suffix in suffixes), (
        f"Response does not contain expected output marker: {response_str}"
    )


def test_text_to_image():
    response = _run_media_tool(
        "text_to_image",
        {
            "prompt": "A tree",
            "width": 624,
            "height": 624,
        },
    )

    # Response should contain a URL to the generated image
    _assert_media_response_has_output(response, (".png", ".jpg", ".jpeg", "image"))


def test_text_to_speech():
    response = _run_media_tool(
        "text_to_speech",
        {
            "text": "Skill Pilot can now generate speech from a reference voice.",
            "emotion": "calm",
            "emotion_sample": "This is a calm and steady narration voice.",
            "ref_voice": str(REF_VOICE),
            #"ref_emotion_voice": "file",
        },
    )

    _assert_media_response_has_output(response, (".wav", ".mp3", "audio"))


def test_text_to_song():
    response = _run_media_tool(
        "text_to_song",
        {
            "lyrics": "[verse]\nSkill Pilot keeps the workflow moving on\n[chorus]\nTurn the prompt into a working song",
            "ref_voice": str(REF_VOICE),
        },
    )

    _assert_media_response_has_output(response, (".wav", ".mp3", "audio"))
