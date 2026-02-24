import asyncio
from typing import Optional
from logger import log


async def get_audio_duration(file_path: str) -> Optional[float]:
    """
    Return duration in seconds for the provided audio file using ffprobe.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        log(f"[AUDIO_DURATION_ERROR] {stderr.decode().strip() or stdout.decode().strip()}")
        return None
    try:
        return float(stdout.decode().strip())
    except ValueError:
        log("[AUDIO_DURATION_PARSE_ERROR] Unable to parse ffprobe output.")
        return None


async def convert_audio_to_mp3(
    input_path: str,
    output_path: str,
    duration_limit: int = 30,
    max_leading_silence: float = 0.4,
) -> None:
    """
    Convert any supported audio file to MP3 while trimming duration and leading silence.
    """
    filters: list[str] = []
    if max_leading_silence is not None and max_leading_silence > 0:
        filters.append(
            f"silenceremove=start_periods=1:start_threshold=-50dB:start_duration={max_leading_silence}"
        )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        input_path,
    ]
    if duration_limit:
        cmd.extend(["-t", str(duration_limit)])
    if filters:
        cmd.extend(["-af", ",".join(filters)])
    cmd.extend(
        [
            "-ac",
            "1",
            "-ar",
            "48000",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "192k",
            output_path,
        ]
    )

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_message = stderr.decode().strip() or stdout.decode().strip() or "ffmpeg conversion failed"
        raise RuntimeError(error_message)


async def merge_audio_files(
    audio_file1_path: str,
    audio_file2_path: str,
    output_path: str,
) -> None:
    """
    Merge two audio files into a single MP3 file by mixing them together.
    Both audio files should have the same duration, with one speaker silent when the other is talking.
    The output will be a mono MP3 file with both speakers mixed together.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        audio_file1_path,
        "-i",
        audio_file2_path,
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0",
        "-ac",
        "1",
        "-ar",
        "48000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        output_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_message = stderr.decode().strip() or stdout.decode().strip() or "ffmpeg audio merge failed"
        raise RuntimeError(error_message)

    log(f"[AUDIO_MERGE] Successfully merged {audio_file1_path} and {audio_file2_path} to {output_path}")
