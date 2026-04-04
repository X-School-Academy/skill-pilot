#!/home/ubuntu/workspace/OmniVoice/.venv/bin/python3
"""
OmniVoice Text-to-Speech Generation Script

This script mirrors the JSON input formats and JSON output shape of
index-tts.py while using OmniVoice as the synthesis backend.

Notes:
- The same JSON input formats are accepted.
- `emotion_sample` and `ref_emotion_voice` are accepted for compatibility
  but ignored because OmniVoice does not support emotion control.
- OmniVoice uses the reference voice audio for voice cloning and will
  auto-transcribe it when reference text is not provided.

JSON INPUT FORMATS:
1. Single text mode:
   {
     "text": "text content",
     "ref_voice": "path/to/voice.wav",
     "emotion_sample": "ignored",
     "ref_emotion_voice": "ignored"
   }

2. Dialog mode:
   {
     "dialog": [
       {
         "text": "utterance text",
         "ref_voice": "path/to/speaker1.wav",
         "emotion_sample": "ignored",
         "ref_emotion_voice": "ignored"
       }
     ]
   }

3. Questions mode:
   {
     "questions": [
       {
         "question": {
           "text": "question text",
           "ref_voice": "path/to/voice.wav"
         },
         "answer": {
           "text": "answer text",
           "ref_voice": "path/to/voice.wav"
         }
       }
     ]
   }

4. Lines mode:
   {
     "ref_voice": "path/to/voice.wav",
     "lines": [
       {
         "text": "line text",
         "emotion": "emotion_name",
         "emotion_sample": "ignored",
         "ref_emotion_voice": "ignored"
       }
     ]
   }

5. Segments mode:
   {
     "ref_voice": "path/to/voice.wav",
     "segments": [
       {
         "text": "segment text",
         "emotion": "emotion_name",
         "emotion_sample": "ignored",
         "ref_emotion_voice": "ignored"
       }
     ]
   }
"""

import argparse
import gc
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import torch
import torchaudio

from omnivoice.models.omnivoice import OmniVoice


MODEL_PATH = "/home/ubuntu/workspace/models/omnivoice"
ASR_MODEL_PATH = "/home/ubuntu/workspace/models/whisper-large-v3-turbo"
DEFAULT_SILENCE_PADDING = 0.5
COMFYUI_INSTALL_PATH = str(os.environ.get("COMFYUI_INSTALL_PATH") or "").strip()
DEFAULT_OUTPUT_DIR = (
    f"{COMFYUI_INSTALL_PATH}/output" if COMFYUI_INSTALL_PATH else "/tmp"
)


def get_best_device() -> str:
    """Auto-detect the best available device: CUDA > MPS > CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def clear_gpu_memory() -> None:
    """Release Python and CUDA memory between multi-item generations."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def resolve_model_source(model_path: str) -> str:
    """
    Resolve the OmniVoice model source.

    The model path is fixed and must exist as a local directory.
    """
    source = str(model_path or "").strip()
    if not source:
        raise ValueError("MODEL_PATH is not configured")

    expanded = Path(source).expanduser()
    if expanded.is_dir():
        return str(expanded)

    raise FileNotFoundError(f"MODEL_PATH directory not found: {expanded}")


def resolve_asr_model_source(asr_model_path: str) -> str:
    """
    Resolve the ASR model source.

    Supports either a Hugging Face model id or a local directory path without
    changing OmniVoice source code.
    """
    source = str(asr_model_path or "").strip()
    if not source:
        raise ValueError("ASR_MODEL_PATH is not configured")

    is_path_like = (
        source.startswith("/")
        or source.startswith(".")
        or source.startswith("~")
        or os.sep in source
        or (os.altsep is not None and os.altsep in source)
    )
    if not is_path_like:
        return source

    expanded = Path(source).expanduser()
    if expanded.is_dir():
        return str(expanded)

    raise FileNotFoundError(f"ASR_MODEL_PATH directory not found: {expanded}")


def init_tts():
    """Initialize the OmniVoice model with the default inference settings."""
    device = get_best_device()
    model_path = resolve_model_source(MODEL_PATH)
    asr_model_path = resolve_asr_model_source(ASR_MODEL_PATH)
    dtype = torch.float16 if device != "cpu" else torch.float32

    print(
        f"Initializing OmniVoice model from {model_path} on {device}...",
        file=sys.stderr,
    )
    model = OmniVoice.from_pretrained(
        model_path,
        device_map=device,
        dtype=dtype,
        load_asr=True,
        asr_model_name=asr_model_path,
    )
    print("OmniVoice model initialized successfully", file=sys.stderr)
    return model


def _edge_silence_durations_seconds(
    waveform: torch.Tensor,
    sample_rate: int,
    threshold: float = 1e-3,
):
    """Return the current leading and trailing silence in seconds."""
    if waveform.numel() == 0:
        return 0.0, 0.0

    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)

    amplitude = waveform.abs().amax(dim=0)
    non_silent_indices = torch.nonzero(amplitude > threshold, as_tuple=False)
    if non_silent_indices.numel() == 0:
        total = waveform.shape[-1] / float(sample_rate)
        return total, total

    first_idx = int(non_silent_indices[0].item())
    last_idx = int(non_silent_indices[-1].item())
    leading = first_idx / float(sample_rate)
    trailing = (waveform.shape[-1] - last_idx - 1) / float(sample_rate)
    return leading, trailing


def pad_audio_file(
    audio_path: str,
    head_silence: float = 0.0,
    tail_silence: Optional[float] = None,
):
    """
    Ensure audio has at least the requested silence at start and end.
    Adds padding only when existing silence is shorter than desired.
    """
    target = head_silence
    tail_target = target if tail_silence is None else tail_silence
    if target <= 0 and tail_target <= 0:
        return audio_path

    waveform, sample_rate = torchaudio.load(audio_path)
    leading_current, trailing_current = _edge_silence_durations_seconds(
        waveform, sample_rate
    )

    leading_needed = max(0.0, target - leading_current)
    trailing_needed = max(0.0, tail_target - trailing_current)

    if leading_needed <= 0 and trailing_needed <= 0:
        return audio_path

    leading = torch.zeros(
        (waveform.shape[0], int(sample_rate * leading_needed)),
        dtype=waveform.dtype,
    )
    trailing = torch.zeros(
        (waveform.shape[0], int(sample_rate * trailing_needed)),
        dtype=waveform.dtype,
    )

    padded = torch.cat([leading, waveform, trailing], dim=1)
    torchaudio.save(audio_path, padded.cpu(), sample_rate)
    return audio_path


def merge_audio_files(
    audio_files,
    output_path,
    mute_indices=None,
    silence_duration=0.0,
):
    """Merge multiple audio files into one with optional muting and silence."""
    print(f"Merging {len(audio_files)} audio files...", file=sys.stderr)

    audio_data = []
    sample_rate = None
    channels = None

    for idx, audio_file in enumerate(audio_files):
        waveform, sr = torchaudio.load(audio_file)

        if sample_rate is None:
            sample_rate = sr
            channels = waveform.shape[0]
        elif sample_rate != sr:
            print(f"Warning: Sample rate mismatch at index {idx}", file=sys.stderr)
            waveform = torchaudio.functional.resample(waveform, sr, sample_rate)

        if mute_indices and idx in mute_indices:
            waveform = torch.zeros_like(waveform)

        audio_data.append(waveform)

        if silence_duration > 0 and idx < len(audio_files) - 1:
            silence = torch.zeros(
                (channels, int(sample_rate * silence_duration)),
                dtype=waveform.dtype,
            )
            audio_data.append(silence)

    merged = torch.cat(audio_data, dim=1)
    torchaudio.save(output_path, merged.cpu(), sample_rate)
    print(f"Merged audio saved: {output_path}", file=sys.stderr)

    del audio_data, merged
    gc.collect()
    return output_path


def generate_audio(
    tts,
    text,
    ref_voice,
    output_path,
    verbose=False,
    pad_seconds: float = 0.0,
):
    """Generate one OmniVoice output using default inference parameters."""
    del verbose  # Compatibility with the index-tts.py call pattern.

    print(f"Generating audio for text: {text[:50]}...", file=sys.stderr)
    print(f"Using reference voice: {ref_voice}", file=sys.stderr)

    audios = tts.generate(
        text=text,
        ref_audio=ref_voice,
        ref_text=None,
        language=None,
        instruct=None,
        duration=None,
        num_step=32,
        guidance_scale=2.0,
        speed=1.0,
        t_shift=0.1,
        denoise=False,
        postprocess_output=True,
        layer_penalty_factor=5.0,
        position_temperature=5.0,
        class_temperature=0.0,
    )
    torchaudio.save(output_path, audios[0].detach().cpu(), tts.sampling_rate)
    print(f"Audio generated: {output_path}", file=sys.stderr)

    if pad_seconds > 0:
        pad_audio_file(output_path, pad_seconds)
    return output_path


def handle_single_text(tts, data, output_dir, pad_seconds: float):
    print("Processing single text input...", file=sys.stderr)

    output_filename = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    generate_audio(
        tts,
        data["text"],
        data["ref_voice"],
        output_filename,
        verbose=True,
        pad_seconds=pad_seconds,
    )
    return {"audio_file": output_filename}


def handle_dialog(tts, data, output_dir, pad_seconds: float):
    dialog = data["dialog"]
    total_utterances = len(dialog)
    print(
        f"Processing dialog with {total_utterances} utterances...",
        file=sys.stderr,
    )

    temp_files = []
    role_map = {}
    role_counter = 0

    for idx, utterance in enumerate(dialog, 1):
        text = utterance["text"]
        ref_voice = utterance["ref_voice"]

        if total_utterances > 20 and idx % 20 == 0:
            print(
                f"Progress: {idx}/{total_utterances} utterances processed "
                f"({idx * 100 // total_utterances}%)",
                file=sys.stderr,
            )

        if ref_voice not in role_map:
            role_counter += 1
            role_map[ref_voice] = role_counter

        temp_filename = str(Path(output_dir) / f"temp_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            text,
            ref_voice,
            temp_filename,
            verbose=False,
            pad_seconds=0.0,
        )
        temp_files.append(temp_filename)
        clear_gpu_memory()

    output1 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    output2 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")

    role1_indices = []
    role2_indices = []
    for idx, utterance in enumerate(dialog):
        if role_map[utterance["ref_voice"]] == 1:
            role1_indices.append(idx)
        else:
            role2_indices.append(idx)

    merge_audio_files(temp_files, output1, mute_indices=set(role2_indices))
    pad_audio_file(output1, pad_seconds)

    gc.collect()

    merge_audio_files(temp_files, output2, mute_indices=set(role1_indices))
    pad_audio_file(output2, pad_seconds)

    for temp_file in temp_files:
        Path(temp_file).unlink(missing_ok=True)

    del temp_files, role1_indices, role2_indices
    clear_gpu_memory()

    print(
        f"Successfully processed dialog with {total_utterances} utterances",
        file=sys.stderr,
    )
    return {"audio_file1": output1, "audio_file2": output2}


def handle_questions(tts, data, output_dir, pad_seconds: float):
    questions = data["questions"]
    total_pairs = len(questions)
    print(f"Processing {total_pairs} Q&A pairs...", file=sys.stderr)

    question_files = []
    answer_files = []

    for idx, qa_pair in enumerate(questions, 1):
        question_data = qa_pair["question"]
        answer_data = qa_pair["answer"]

        if total_pairs > 10 and idx % 10 == 0:
            print(
                f"Progress: {idx}/{total_pairs} Q&A pairs processed "
                f"({idx * 100 // total_pairs}%)",
                file=sys.stderr,
            )

        q_temp = str(Path(output_dir) / f"temp_q_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            question_data["text"],
            question_data["ref_voice"],
            q_temp,
            verbose=False,
            pad_seconds=0.0,
        )
        question_files.append(q_temp)
        clear_gpu_memory()

        a_temp = str(Path(output_dir) / f"temp_a_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            answer_data["text"],
            answer_data["ref_voice"],
            a_temp,
            verbose=False,
            pad_seconds=0.0,
        )
        answer_files.append(a_temp)
        clear_gpu_memory()

    all_files = []
    for question_file, answer_file in zip(question_files, answer_files):
        all_files.append(question_file)
        all_files.append(answer_file)

    output1 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    output2 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")

    answer_indices = [i for i in range(len(all_files)) if i % 2 == 1]
    merge_audio_files(all_files, output1, mute_indices=set(answer_indices))
    pad_audio_file(output1, pad_seconds)

    gc.collect()

    question_indices = [i for i in range(len(all_files)) if i % 2 == 0]
    merge_audio_files(all_files, output2, mute_indices=set(question_indices))
    pad_audio_file(output2, pad_seconds)

    for temp_file in all_files:
        Path(temp_file).unlink(missing_ok=True)

    del all_files, question_files, answer_files
    clear_gpu_memory()

    print(f"Successfully processed all {total_pairs} Q&A pairs", file=sys.stderr)
    return {"audio_file1": output1, "audio_file2": output2}


def handle_segments(tts, data, output_dir, pad_seconds: float):
    segments = data["segments"]
    total_segments = len(segments)
    ref_voice = data["ref_voice"]
    print(
        f"Processing {total_segments} segments with single voice...",
        file=sys.stderr,
    )

    audio_files = []

    for idx, segment in enumerate(segments, 1):
        text = segment["text"]
        emotion = str(segment.get("emotion") or "").strip()
        emotion_sample = str(segment.get("emotion_sample") or "").strip()

        if not str(text or "").strip():
            raise ValueError(f"Segment {idx} missing text")
        if not emotion:
            raise ValueError(f"Segment {idx} missing emotion")
        if not emotion_sample:
            raise ValueError(f"Segment {idx} missing emotion_sample")

        if total_segments > 20 and idx % 20 == 0:
            print(
                f"Progress: {idx}/{total_segments} segments processed "
                f"({idx * 100 // total_segments}%)",
                file=sys.stderr,
            )
        elif total_segments <= 20:
            print(
                f"Processing segment {idx}/{total_segments}: {text[:30]}...",
                file=sys.stderr,
            )

        output_filename = str(Path(output_dir) / f"segment_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            text,
            ref_voice,
            output_filename,
            verbose=False,
            pad_seconds=pad_seconds,
        )
        audio_files.append(output_filename)
        clear_gpu_memory()

    print(
        f"Successfully processed all {total_segments} segments",
        file=sys.stderr,
    )
    return {"audio_files": audio_files}


def handle_lines(tts, data, output_dir, pad_seconds: float):
    lines = data["lines"]
    total_lines = len(lines)
    ref_voice = data["ref_voice"]
    print(f"Processing {total_lines} lines with single voice...", file=sys.stderr)

    temp_files = []

    for idx, line in enumerate(lines, 1):
        text = line["text"]
        emotion = str(line.get("emotion") or "").strip()
        emotion_sample = str(line.get("emotion_sample") or "").strip()

        if not str(text or "").strip():
            raise ValueError(f"Line {idx} missing text")
        if not emotion:
            raise ValueError(f"Line {idx} missing emotion")
        if not emotion_sample:
            raise ValueError(f"Line {idx} missing emotion_sample")

        if total_lines > 20 and idx % 20 == 0:
            print(
                f"Progress: {idx}/{total_lines} lines processed "
                f"({idx * 100 // total_lines}%)",
                file=sys.stderr,
            )
        elif total_lines <= 20:
            print(
                f"Processing line {idx}/{total_lines}: {text[:30]}...",
                file=sys.stderr,
            )

        temp_filename = str(Path(output_dir) / f"temp_line_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            text,
            ref_voice,
            temp_filename,
            verbose=False,
            pad_seconds=0.0,
        )
        temp_files.append(temp_filename)
        clear_gpu_memory()

    output_file = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    merge_audio_files(temp_files, output_file, silence_duration=0.5)
    pad_audio_file(output_file, pad_seconds)

    for temp_file in temp_files:
        Path(temp_file).unlink(missing_ok=True)

    del temp_files
    clear_gpu_memory()

    print(f"Successfully processed all {total_lines} lines", file=sys.stderr)
    return {"audio_file": output_file}


def main():
    parser = argparse.ArgumentParser(description="TTS generation script")
    parser.add_argument("--json-str", required=True, help="JSON string input")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for generated audio files",
    )
    parser.add_argument(
        "--pad-seconds",
        type=float,
        default=DEFAULT_SILENCE_PADDING,
        help="Seconds of silence to pad at start and end of each output audio file",
    )
    args = parser.parse_args()

    try:
        data = json.loads(args.json_str)

        output_dir = Path(str(data.get("output_dir") or args.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        tts = init_tts()

        if "segments" in data:
            result = handle_segments(tts, data, str(output_dir), args.pad_seconds)
        elif "lines" in data:
            result = handle_lines(tts, data, str(output_dir), args.pad_seconds)
        elif "dialog" in data:
            result = handle_dialog(tts, data, str(output_dir), args.pad_seconds)
        elif "questions" in data:
            result = handle_questions(tts, data, str(output_dir), args.pad_seconds)
        else:
            result = handle_single_text(tts, data, str(output_dir), args.pad_seconds)

        print(f"<json-output>{json.dumps(result)}</json-output>")

    except Exception as exc:
        print(f"Error: {str(exc)}", file=sys.stderr)
        print(f"<json-output>{json.dumps({'error': str(exc)})}</json-output>")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
