import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

def test_create_simple_video():
    CPU_VIDEO_PAYLOAD = {
        "requirement": "Create a short educational video explaining what CPU video generation means and when to use it.",
        "target_duration": 60,
        "resolution": "1920x1080",
    }
    command = [
        "core/bin/api-invoke",
        "create_multiple_scene_video",
        json.dumps(CPU_VIDEO_PAYLOAD, ensure_ascii=False),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    print("--- stdout ---")
    print(result.stdout)
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr)

    assert result.returncode == 0, f"api-invoke failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "No output returned from api-invoke"

    response = json.loads(output)
    assert isinstance(response, dict), f"Expected JSON object, got: {output}"

    video_file_path = response.get("video_file_path")
    assert isinstance(video_file_path, str), f"Expected string video_file_path, got: {response}"
    assert video_file_path.strip(), f"Expected non-empty video_file_path, got: {response}"
