#!/home/frankhe/data/AUTOMATIC1111/remove-music/.venv/bin/python
"""
Demucs Vocal Extraction Script

# pyproject.toml
[project]
requires-python = ">=3.10"
dependencies = [
    "demucs>=4.0.1",
    "numpy>=2.2.6",
]
[tool.uv.sources]
demucs = { git = "https://github.com/adefossez/demucs" }


This script provides a command-line interface for extracting vocals from audio files using Demucs.

JSON INPUT FORMAT:
{
  "audio_file": "path/to/audio.wav",
  "output_dir": "/tmp"  # optional, defaults to /tmp
}

OUTPUT FORMAT:
{
  "vocals_file": "path/to/vocals.wav"
}

SUPPORTED FORMATS:
- Input: MP3, WAV, FLAC, M4A, and other common audio formats
- Output: WAV format (high quality)
"""
import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import torch
import numpy as np
import soundfile as sf
import demucs.api

COMFYUI_INSTALL_PATH = str(os.environ.get("COMFYUI_INSTALL_PATH") or "").strip()
DEFAULT_OUTPUT_DIR = f"{COMFYUI_INSTALL_PATH}/output" if COMFYUI_INSTALL_PATH else "/tmp"

def extract_vocals(audio_file: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
    """
    Extract vocals from an audio file using Demucs.

    Args:
        audio_file: Path to the input audio file (MP3, WAV, etc.)
        output_dir: Directory where the vocals file will be saved

    Returns:
        dict: {'vocals_file': path_to_vocals_audio}
    """
    print(f"Extracting vocals from: {audio_file}", file=sys.stderr)

    # Validate input file exists
    audio_path = Path(audio_file).expanduser()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize Demucs separator
    print("Initializing Demucs separator...", file=sys.stderr)
    separator = demucs.api.Separator()

    # Separate audio into stems
    print("Separating audio into stems (this may take a while)...", file=sys.stderr)
    _, separated = separator.separate_audio_file(str(audio_path))

    # Extract vocals stem
    if 'vocals' not in separated:
        raise ValueError("Vocals stem not found in separated audio")

    vocals_source = separated['vocals']

    # Generate unique filename for vocals
    vocals_filename = output_path / f"vocals_{uuid.uuid4()}.wav"

    # Save vocals to file
    print(f"Saving vocals to: {vocals_filename}", file=sys.stderr)
    # Convert to numpy array for soundfile
    if isinstance(vocals_source, torch.Tensor):
        vocals_array = vocals_source.cpu().numpy()
    else:
        vocals_array = np.array(vocals_source)

    # Ensure shape is (samples, channels) for soundfile
    if vocals_array.ndim == 1:
        vocals_array = vocals_array.reshape(-1, 1)
    elif vocals_array.shape[0] < vocals_array.shape[1]:
        # If channels first (C, T), transpose to (T, C)
        vocals_array = vocals_array.T

    # Save using soundfile
    sf.write(
        str(vocals_filename),
        vocals_array,
        samplerate=separator.samplerate
    )

    print(f"Vocals extracted successfully: {vocals_filename}", file=sys.stderr)

    return {
        'vocals_file': str(vocals_filename)
    }


def main():
    parser = argparse.ArgumentParser(description='Demucs vocal extraction script')
    parser.add_argument('--json-str', required=True, help='JSON string input')
    args = parser.parse_args()

    try:
        # Parse JSON input
        data = json.loads(args.json_str)

        # Extract parameters
        audio_file = data.get('audio_file')
        if not audio_file:
            raise ValueError("audio_file is required in JSON input")

        output_dir = data.get('output_dir', DEFAULT_OUTPUT_DIR)

        # Process audio
        result = extract_vocals(audio_file, output_dir)

        # Output result in the specified format
        print(f"<json-output>{json.dumps(result)}</json-output>")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        # Output error in JSON format
        error_output = {
            'error': str(e)
        }
        print(f"<json-output>{json.dumps(error_output)}</json-output>")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
