import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REF_VOICE = "assets/custom-voices/angelina-speech-en.mp3"


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
    response_str = json.dumps(response, ensure_ascii=False)
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


def test_image_to_image():
    response = _run_media_tool(
        "image_to_image",
        {
            "prompt": "A tree in the winter and snow",
            "image_file": "/private/tmp/mcp_video_http_outputs/acb5a92b52474c9eac48a8c24b48530f.png"
        },
    )

    # Response should contain a URL to the generated image
    _assert_media_response_has_output(response, (".png", ".jpg", ".jpeg", "image"))


# 5:49 mins used 11:04 mins
def test_text_to_speech():
    response = _run_media_tool(
        "text_to_speech",
        {
            "text": "Today, we're going to talk about the very first step of onboarding any new employee.",
            "emotion": "calm",
            "emotion_sample": "This is a calm and steady narration voice.",
            "ref_voice": str(REF_VOICE),
            "ref_emotion_voice": str(REF_VOICE),
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

def test_audio_segments():
    response = _run_media_tool(
        "audio_segments",
        {
            "audio_file": "/Users/frankhe/Downloads/vvv.mp3",
            "language": "zh",
        },
    )

    _assert_media_response_has_output(response, ("start"))


# 1920x1080 - 19s: 52 mins 
def test_image2talking_video():
    response = _run_media_tool(
        "image_to_talk_video",
        {
            "prompt": "Professional man speaking naturally in a landscape setting, maintaining steady eye contact and clear articulation.",
            "image_file": "assets/images/frank-landscape.png",
            "audio_file": "assets/custom-voices/frank-en.mp3",
            "width": 1920,
            "height": 1080,
        },
    )

    _assert_media_response_has_output(response, (".mp4", "video"))

# 1920x1080 - 19s: 33 mins 
def test_video2talking_video():
    response = _run_media_tool(
        "video_to_talk_video",
        {
            "prompt": "Professional man speaking naturally in a landscape setting, maintaining steady eye contact and clear articulation.",
            "video_file": "assets/videos/frank-ai1.mp4",
            "audio_file": "assets/custom-voices/frank-en.mp3",
            "width": 1920,
            "height": 1080,
        },
    )

    _assert_media_response_has_output(response, (".mp4", "video"))

# 1280x720   1:50 mins - 23 mins
# 960x528    5:49 mins - 34 mins 
def test_video_lipsync():
    response = _run_media_tool(
        "video_lipsync",
        {
            "video_file": "workspace/tasks/au/aa-10.mp4",
            "audio_file": "workspace/tasks/au/fb9778a3-b1fe-4619-98e5-3da1ebb3c8a6.wav",
        },
    )

    _assert_media_response_has_output(response, (".mp4", "video"))
