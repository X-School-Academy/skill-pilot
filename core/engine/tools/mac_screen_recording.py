#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATE_PATH = PROJECT_ROOT / ".skillpilot" / "temp" / "screen-recording" / "state.json"
DEFAULT_RECORDINGS_DIR = PROJECT_ROOT / ".skillpilot" / "temp" / "screen-recording" / "recordings"
DEFAULT_FPS = 30


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("mac-screen-recording is only supported on macOS")


def _require_binary(name: str) -> str:
    resolved = shutil.which(name)
    if not resolved:
        raise RuntimeError(f"Required binary not found in PATH: {name}")
    return resolved


def _run(cmd: list[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def _state_path(path_arg: Optional[str]) -> Path:
    if not path_arg:
        return DEFAULT_STATE_PATH
    path = Path(path_arg).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _write_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
    os.replace(tmp, path)


def _tmux_session_exists(session: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def _tmux_new_session(session: str, command: str) -> None:
    _run(["tmux", "new-session", "-d", "-s", session, command], check=True, capture_output=True)


def _tmux_send_ctrl_c(session: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", session, "C-c"], capture_output=True, text=True)


def _tmux_kill_session(session: str) -> None:
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True, text=True)


def _wait_for_tmux_exit(session: str, timeout_s: float = 8.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not _tmux_session_exists(session):
            return True
        time.sleep(0.25)
    return not _tmux_session_exists(session)


def _discover_main_screen_device(ffmpeg: str) -> str:
    # ffmpeg prints device list to stderr for avfoundation.
    proc = subprocess.run(
        [ffmpeg, "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        text=True,
        capture_output=True,
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")

    match_main = re.search(r"\[(\d+)\]\s+Capture screen\s+0", text, re.IGNORECASE)
    if match_main:
        return match_main.group(1)

    match_any = re.search(r"\[(\d+)\]\s+Capture screen\s+\d+", text, re.IGNORECASE)
    if match_any:
        return match_any.group(1)

    raise RuntimeError("Unable to auto-detect a 'Capture screen' avfoundation input device from ffmpeg")


def _build_start_payload(
    state_path: Path,
    run_id: str,
    output_file: Path,
    recording_dir: Path,
    video_session: str,
    audio_session: str,
    ffmpeg: str,
    sox: str,
    fps: int,
    forced_screen_device_index: Optional[str],
) -> Dict[str, Any]:
    video_file = recording_dir / "video.mp4"
    audio_file = recording_dir / "audio.wav"
    muxed_file = recording_dir / "muxed.mp4"

    warning = None
    if forced_screen_device_index is not None:
        screen_device_index = forced_screen_device_index
    else:
        try:
            screen_device_index = _discover_main_screen_device(ffmpeg)
        except RuntimeError:
            # Common fallback on macOS: screen capture device index 1.
            screen_device_index = "1"
            warning = "Could not auto-detect main screen device. Falling back to screen index 1."

    ffmpeg_cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "avfoundation",
        "-framerate",
        str(fps),
        "-capture_cursor",
        "1",
        "-capture_mouse_clicks",
        "1",
        "-i",
        f"{screen_device_index}:none",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        str(video_file),
    ]

    sox_cmd = [
        sox,
        "-q",
        "-t",
        "coreaudio",
        "default",
        "-c",
        "1",
        "-r",
        "48000",
        str(audio_file),
    ]

    return {
        "status": "recording",
        "run_id": run_id,
        "started_at": _utc_now_iso(),
        "state_path": str(state_path),
        "recording_dir": str(recording_dir),
        "output_file": str(output_file),
        "video_file": str(video_file),
        "audio_file": str(audio_file),
        "muxed_file": str(muxed_file),
        "video_session": video_session,
        "audio_session": audio_session,
        "screen_device_index": screen_device_index,
        "warning": warning,
        "ffmpeg_cmd": ffmpeg_cmd,
        "sox_cmd": sox_cmd,
    }


def _start(args: argparse.Namespace) -> int:
    _require_macos()
    ffmpeg = _require_binary("ffmpeg")
    _require_binary("sox")
    _require_binary("tmux")

    state_path = _state_path(args.state_path)
    state = _load_state(state_path)
    if state.get("status") == "recording":
        video_session = state.get("video_session")
        if video_session and _tmux_session_exists(video_session):
            raise RuntimeError("A recording is already running; stop it before starting a new one")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    recordings_dir = Path(args.recordings_dir) if args.recordings_dir else DEFAULT_RECORDINGS_DIR
    recording_dir = recordings_dir / run_id
    recording_dir.mkdir(parents=True, exist_ok=True)

    output_file = Path(args.output) if args.output else (recording_dir / "recording.mp4")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    video_session = f"screen-rec-video-{run_id}"
    audio_session = f"screen-rec-audio-{run_id}"

    payload = _build_start_payload(
        state_path=state_path,
        run_id=run_id,
        output_file=output_file,
        recording_dir=recording_dir,
        video_session=video_session,
        audio_session=audio_session,
        ffmpeg=ffmpeg,
        sox=_require_binary("sox"),
        fps=max(1, int(args.fps)),
        forced_screen_device_index=args.screen_device_index,
    )

    video_cmd = "cd " + shlex.quote(os.getcwd()) + " && " + shlex.join(payload["ffmpeg_cmd"])
    audio_cmd = "cd " + shlex.quote(os.getcwd()) + " && " + shlex.join(payload["sox_cmd"])

    _tmux_new_session(video_session, video_cmd)
    _tmux_new_session(audio_session, audio_cmd)

    # If either process exits immediately, surface that as a startup failure.
    time.sleep(0.6)
    if not _tmux_session_exists(video_session):
        _tmux_kill_session(audio_session)
        raise RuntimeError("Video recording session exited immediately; check screen recording permissions")

    if not _tmux_session_exists(audio_session):
        _tmux_send_ctrl_c(video_session)
        _tmux_kill_session(video_session)
        raise RuntimeError("Audio recording session exited immediately; check microphone permissions/device")

    _write_state(state_path, payload)

    print(
        json.dumps(
            {
                "status": "recording",
                "run_id": run_id,
                "output_file": payload["output_file"],
                "video_session": video_session,
                "audio_session": audio_session,
                "screen_device_index": payload["screen_device_index"],
                "warning": payload.get("warning"),
            },
            ensure_ascii=True,
        )
    )
    return 0


def _stop(args: argparse.Namespace) -> int:
    _require_macos()
    ffmpeg = _require_binary("ffmpeg")
    _require_binary("tmux")

    state_path = _state_path(args.state_path)
    state = _load_state(state_path)
    if not state or state.get("status") != "recording":
        raise RuntimeError(f"No active recording state found at {state_path}")

    video_session = state.get("video_session")
    audio_session = state.get("audio_session")

    if video_session:
        _tmux_send_ctrl_c(video_session)
    if audio_session:
        _tmux_send_ctrl_c(audio_session)

    if video_session and not _wait_for_tmux_exit(video_session):
        _tmux_kill_session(video_session)
    if audio_session and not _wait_for_tmux_exit(audio_session):
        _tmux_kill_session(audio_session)

    video_file = Path(state["video_file"])
    audio_file = Path(state["audio_file"])
    muxed_file = Path(state["muxed_file"])
    output_file = Path(state["output_file"])

    if video_file.exists() and audio_file.exists() and audio_file.stat().st_size > 0:
        _run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video_file),
                "-i",
                str(audio_file),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(muxed_file),
            ],
            check=True,
            capture_output=True,
        )
        shutil.move(str(muxed_file), str(output_file))
    elif video_file.exists():
        shutil.copy2(video_file, output_file)
    else:
        raise RuntimeError("No video file produced by ffmpeg; recording may have failed")

    state["status"] = "stopped"
    state["stopped_at"] = _utc_now_iso()
    state["final_file"] = str(output_file)
    _write_state(state_path, state)

    print(
        json.dumps(
            {
                "status": "stopped",
                "run_id": state.get("run_id"),
                "final_file": str(output_file),
                "video_exists": video_file.exists(),
                "audio_exists": audio_file.exists(),
            },
            ensure_ascii=True,
        )
    )
    return 0


def _status(args: argparse.Namespace) -> int:
    state_path = _state_path(args.state_path)
    state = _load_state(state_path)
    if not state:
        print(json.dumps({"status": "idle", "state_path": str(state_path)}, ensure_ascii=True))
        return 0

    video_session = state.get("video_session")
    audio_session = state.get("audio_session")
    session_video_running = bool(video_session and _tmux_session_exists(video_session))
    session_audio_running = bool(audio_session and _tmux_session_exists(audio_session))

    print(
        json.dumps(
            {
                "status": state.get("status", "unknown"),
                "state_path": str(state_path),
                "run_id": state.get("run_id"),
                "output_file": state.get("output_file"),
                "video_session_running": session_video_running,
                "audio_session_running": session_audio_running,
            },
            ensure_ascii=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="macOS screen recording CLI (main monitor only) using tmux, ffmpeg, and sox"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start recording in background tmux sessions")
    start_parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help="Video frame rate (default: 30)")
    start_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Final output mp4 path (default: .skillpilot/temp/screen-recording/recordings/<run_id>/recording.mp4)",
    )
    start_parser.add_argument(
        "--screen-device-index",
        type=str,
        default=None,
        help="Override avfoundation screen input index (use when auto-detection fails).",
    )
    start_parser.add_argument(
        "--recordings-dir",
        type=str,
        default=str(DEFAULT_RECORDINGS_DIR),
        help="Base directory for per-run recording files",
    )
    start_parser.add_argument(
        "--state-path",
        type=str,
        default=str(DEFAULT_STATE_PATH),
        help="State file path used for start/stop communication",
    )

    stop_parser = subparsers.add_parser("stop", help="Stop active recording and mux output")
    stop_parser.add_argument(
        "--state-path",
        type=str,
        default=str(DEFAULT_STATE_PATH),
        help="State file path used for start/stop communication",
    )

    status_parser = subparsers.add_parser("status", help="Show recording status")
    status_parser.add_argument(
        "--state-path",
        type=str,
        default=str(DEFAULT_STATE_PATH),
        help="State file path used for start/stop communication",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "start":
            return _start(args)
        if args.command == "stop":
            return _stop(args)
        if args.command == "status":
            return _status(args)
        raise RuntimeError(f"Unknown command: {args.command}")
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
