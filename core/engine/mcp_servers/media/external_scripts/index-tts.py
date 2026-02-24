#!/media/frankhe/Data/AUTOMATIC1111/index-tts2/.venv/bin/python3
"""
IndexTTS2 Text-to-Speech Generation Script

This script provides a command-line interface for generating speech using IndexTTS2.
It supports multiple input modes: single text, dialog, questions, and lines.

IMPORTANT AUDIO DURATION LIMITS:
- Reference voice audio (ref_voice): Maximum 15 seconds (auto-truncated if longer)
- Reference emotion audio (ref_emotion_voice): Maximum 15 seconds (auto-truncated if longer)

EMOTION CONTROL:
Each text sample supports two optional emotion parameters:
1. emotion_sample (str): Text description of emotion (e.g., "happy", "sad", "excited")
2. ref_emotion_voice (str): Path to audio file for emotion reference
   - If ref_emotion_voice is set (not null), it will be used as the emotion reference
   - If ref_emotion_voice is set, the emotion_sample text field will be ignored
   - If ref_emotion_voice is null/not set, ref_voice will be used as ref_emotion_voice

JSON INPUT FORMATS:
1. Single text mode:
   {
     "text": "text content",
     "ref_voice": "path/to/voice.wav",
     "emotion_sample": "happy and excited",  # optional
     "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
   }

2. Dialog mode:
   {
     "dialog": [
       {
         "text": "utterance text",
         "ref_voice": "path/to/speaker1.wav",
         "emotion_sample": "cheerful",  # optional
         "ref_emotion_voice": "path/to/emotion1.wav"  # optional
       },
       ...
     ]
   }

3. Questions mode:
   {
     "questions": [
       {
         "question": {
           "text": "question text",
           "ref_voice": "path/to/voice.wav",
           "emotion_sample": "curious",  # optional
           "ref_emotion_voice": "path/to/emotion.wav"  # optional
         },
         "answer": {
           "text": "answer text",
           "ref_voice": "path/to/voice.wav",
           "emotion_sample": "confident",  # optional
           "ref_emotion_voice": "path/to/emotion.wav"  # optional
         }
       },
       ...
     ]
   }

4. Lines mode:
   {
     "ref_voice": "path/to/voice.wav",
     "lines": [
       {
         "text": "line text",
         "emotion": "emotion_name",  # required
         "emotion_sample": "emotion description",  # required
         "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
       },
       ...
     ]
   }
5. Segments mode:
   {
     "ref_voice": "path/to/voice.wav",
     "segments": [
       {
         "text": "line text",
         "emotion": "emotion_name",  # required
          "emotion_sample": "emotion description",  # required
          "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
        },
        ...
      ]
    }
   Returns:
   {
     "audio_files": ["segment1.wav", "segment2.wav", ...]  # array of per-segment audio paths
   }
"""
import argparse
import json
import sys
import uuid
from pathlib import Path
import os
import gc
from typing import Optional

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Change to script directory to ensure all relative paths work correctly
# This is necessary because the config.yaml and imported modules use relative paths
os.chdir(SCRIPT_DIR)

from indextts.infer_v2 import IndexTTS2
import numpy as np
from scipy.io import wavfile
import warnings
import torch

warnings.filterwarnings('ignore')

DEFAULT_SILENCE_PADDING = 0.5
COMFYUI_INSTALL_PATH = str(os.environ.get("COMFYUI_INSTALL_PATH") or "").strip()
DEFAULT_OUTPUT_DIR = f"{COMFYUI_INSTALL_PATH}/output" if COMFYUI_INSTALL_PATH else "/tmp"


def clear_gpu_memory(tts=None):
    """Aggressively clear GPU memory to prevent OOM errors"""
    # Clear TTS model's internal cache if provided
    if tts is not None:
        tts.cache_spk_cond = None
        tts.cache_s2mel_style = None
        tts.cache_s2mel_prompt = None
        tts.cache_spk_audio_prompt = None
        tts.cache_mel = None
        tts.cache_emo_cond = None
        tts.cache_emo_audio_prompt = None

    # Run garbage collection to free Python objects
    gc.collect()

    # Clear CUDA cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def init_tts():
    """Initialize the TTS model"""
    print("Initializing TTS model...", file=sys.stderr)
    tts = IndexTTS2(
        cfg_path=str(SCRIPT_DIR / "checkpoints" / "config.yaml"),
        model_dir=str(SCRIPT_DIR / "checkpoints"),
        use_fp16=False,
        use_cuda_kernel=False,
        use_deepspeed=False
    )
    print("TTS model initialized successfully", file=sys.stderr)
    return tts


def generate_audio(tts, text, emo_text, ref_voice, output_path, ref_emotion_voice=None, verbose=False, pad_seconds: float = 0.0):
    """
    Generate audio using TTS with memory-efficient parameters.

    Args:
        tts: IndexTTS2 model instance
        text (str): Text content to synthesize
        emo_text (str): Emotion text description (ignored if ref_emotion_voice is set)
        ref_voice (str): Path to reference voice audio file (max 15 seconds, auto-truncated)
        output_path (str): Path where generated audio will be saved
        ref_emotion_voice (str, optional): Path to emotion reference audio file (max 15 seconds, auto-truncated)
            - If provided (not None), uses this audio file for emotion reference
            - If provided, the emo_text parameter will be ignored
            - If None/empty, callers can provide a fallback (e.g., reuse ref_voice) or rely on emo_text
        verbose (bool): Enable verbose logging

    Returns:
        str: Path to the generated audio file

    Note:
        Audio files are automatically truncated to 15 seconds maximum by IndexTTS2.
        This limit applies to both ref_voice and ref_emotion_voice files.
    """
    print(f"Generating audio for text: {text[:50]}...", file=sys.stderr)
    print(f"Using reference voice: {ref_voice}", file=sys.stderr)

    # Determine emotion control mode based on ref_emotion_voice
    if ref_emotion_voice:
        # Use emotion audio reference (emo_text will be ignored)
        print(f"Using emotion audio reference: {ref_emotion_voice}", file=sys.stderr)
        use_emo_text = False
        emo_audio_prompt = ref_emotion_voice
        emo_text_param = None
    else:
        # Use emotion text description
        print(f"Emotion text: {emo_text}", file=sys.stderr)
        use_emo_text = True
        emo_audio_prompt = None
        emo_text_param = emo_text

    # Use memory-efficient generation parameters to prevent OOM
    # num_beams=1 uses greedy/sampling instead of beam search, which is much more memory efficient
    tts.infer(
        spk_audio_prompt=ref_voice,
        text=text,
        output_path=output_path,
        emo_alpha=0.6,
        use_emo_text=use_emo_text,
        emo_text=emo_text_param,
        emo_audio_prompt=emo_audio_prompt,
        use_random=False,
        verbose=verbose,
        # Memory-efficient generation parameters for multi-inference scenarios
        num_beams=1,  # Use greedy/sampling instead of beam search to save memory
        do_sample=True,
        top_p=0.8,
        top_k=30,
        temperature=0.8,
        repetition_penalty=10.0,
    )
    print(f"Audio generated: {output_path}", file=sys.stderr)
    if pad_seconds > 0:
        pad_audio_file(output_path, pad_seconds)
    return output_path


def _edge_silence_durations_seconds(data: np.ndarray, sample_rate: int, threshold: float = 1e-3):
    """Return (leading_silence_seconds, trailing_silence_seconds)."""
    if data.size == 0:
        return 0.0, 0.0

    max_val = float(np.iinfo(data.dtype).max) if np.issubdtype(data.dtype, np.integer) else 1.0
    normalized = np.abs(data.astype(np.float32)) / max_val
    if normalized.ndim > 1:
        normalized = normalized.max(axis=1)

    non_silent_indices = np.flatnonzero(normalized > threshold)
    if non_silent_indices.size == 0:
        total = data.shape[0] / float(sample_rate)
        return total, total

    first_idx = int(non_silent_indices[0])
    last_idx = int(non_silent_indices[-1])

    leading = first_idx / float(sample_rate)
    trailing = (data.shape[0] - last_idx - 1) / float(sample_rate)
    return leading, trailing


def pad_audio_file(audio_path: str, head_silence: float = 0.0, tail_silence: Optional[float] = None):
    """
    Ensure audio has at least the requested silence at start and end.
    Adds padding only when existing silence is shorter than desired.
    """
    target = head_silence
    tail_target = target if tail_silence is None else tail_silence
    if target <= 0 and tail_target <= 0:
        return audio_path

    sample_rate, data = wavfile.read(audio_path)
    leading_current, trailing_current = _edge_silence_durations_seconds(data, sample_rate)

    leading_needed = max(0.0, target - leading_current)
    trailing_needed = max(0.0, tail_target - trailing_current)

    if leading_needed <= 0 and trailing_needed <= 0:
        return audio_path

    pad_shape = (data.shape[1],) if data.ndim > 1 else ()
    leading = np.zeros((int(sample_rate * leading_needed), *pad_shape), dtype=data.dtype) if leading_needed > 0 else np.empty((0, *pad_shape), dtype=data.dtype)
    trailing = np.zeros((int(sample_rate * trailing_needed), *pad_shape), dtype=data.dtype) if trailing_needed > 0 else np.empty((0, *pad_shape), dtype=data.dtype)

    padded = np.concatenate([leading, data, trailing])
    wavfile.write(audio_path, sample_rate, padded)
    return audio_path


def merge_audio_files(audio_files, output_path, mute_indices=None, silence_duration=0.0):
    """Merge multiple audio files into one, with optional muting of certain indices and silence between files"""
    print(f"Merging {len(audio_files)} audio files...", file=sys.stderr)

    audio_data = []
    sample_rate = None

    for idx, audio_file in enumerate(audio_files):
        sr, data = wavfile.read(audio_file)

        if sample_rate is None:
            sample_rate = sr
        elif sample_rate != sr:
            print(f"Warning: Sample rate mismatch at index {idx}", file=sys.stderr)

        # Mute if this index should be muted
        if mute_indices and idx in mute_indices:
            data = np.zeros_like(data)

        audio_data.append(data)

        # Add silence between audio files (except after the last one)
        if silence_duration > 0 and idx < len(audio_files) - 1:
            silence_samples = int(sample_rate * silence_duration)
            silence = np.zeros(silence_samples, dtype=data.dtype)
            audio_data.append(silence)

    # Concatenate all audio data
    merged = np.concatenate(audio_data)

    # Explicitly free the audio_data list to release memory before writing
    del audio_data
    gc.collect()

    # Write merged audio
    wavfile.write(output_path, sample_rate, merged)
    print(f"Merged audio saved: {output_path}", file=sys.stderr)

    # Free the merged array
    del merged
    gc.collect()

    return output_path


def handle_single_text(tts, data, output_dir, pad_seconds: float):
    """
    Handle single text input mode.

    Expected JSON structure:
    {
        "text": "text content",
        "ref_voice": "path/to/voice.wav",
        "emotion_sample": "emotion description",  # optional
        "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
    }

    Args:
        tts: IndexTTS2 model instance
        data (dict): Input data containing text, ref_voice, and optional emotion parameters
        output_dir (str): Directory where output audio will be saved

    Returns:
        dict: {'audio_file': path_to_generated_audio}
    """
    print("Processing single text input...", file=sys.stderr)

    text = data['text']
    emo_text = data.get('emotion_sample', '')
    ref_voice = data['ref_voice']
    ref_emotion_voice = data.get('ref_emotion_voice') or ref_voice  # Optional: defaults to ref_voice

    # Generate output filename with UUID
    output_filename = str(Path(output_dir) / f"{uuid.uuid4()}.wav")

    # Generate audio
    generate_audio(
        tts,
        text,
        emo_text,
        ref_voice,
        output_filename,
        ref_emotion_voice=ref_emotion_voice,
        verbose=True,
        pad_seconds=pad_seconds,
    )

    return {
        'audio_file': output_filename
    }


def handle_dialog(tts, data, output_dir, pad_seconds: float):
    """
    Handle dialog mode with multiple speakers.

    Expected JSON structure:
    {
        "dialog": [
            {
                "text": "utterance text",
                "ref_voice": "path/to/speaker.wav",
                "emotion_sample": "emotion description",  # optional
                "ref_emotion_voice": "path/to/emotion.wav"  # optional
            },
            ...
        ]
    }

    Creates two audio files:
    - audio_file1: Contains only utterances from the first speaker (role 1)
    - audio_file2: Contains only utterances from the second speaker (role 2)

    Speakers are automatically assigned roles based on their ref_voice file path.

    Args:
        tts: IndexTTS2 model instance
        data (dict): Input data containing dialog array
        output_dir (str): Directory where output audio will be saved

    Returns:
        dict: {'audio_file1': path_to_role1_audio, 'audio_file2': path_to_role2_audio}
    """
    dialog = data['dialog']
    total_utterances = len(dialog)
    print(f"Processing dialog with {total_utterances} utterances...", file=sys.stderr)

    temp_files = []

    # Determine roles based on ref_voice
    role_map = {}
    role_counter = 0

    for idx, utterance in enumerate(dialog, 1):
        text = utterance['text']
        emo_text = utterance.get('emotion_sample', '')
        ref_voice = utterance['ref_voice']
        ref_emotion_voice = utterance.get('ref_emotion_voice') or ref_voice  # Optional: defaults to ref_voice

        # Progress logging for large batches
        if total_utterances > 20 and idx % 20 == 0:
            print(f"Progress: {idx}/{total_utterances} utterances processed ({idx*100//total_utterances}%)", file=sys.stderr)

        # Assign role based on ref_voice
        if ref_voice not in role_map:
            role_counter += 1
            role_map[ref_voice] = role_counter

        # Generate temporary audio file
        temp_filename = str(Path(output_dir) / f"temp_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            text,
            emo_text,
            ref_voice,
            temp_filename,
            ref_emotion_voice=ref_emotion_voice,
            verbose=False,
            pad_seconds=0.0,
        )
        temp_files.append(temp_filename)

        # Aggressively clear GPU memory to prevent VRAM accumulation
        clear_gpu_memory(tts)

    # Create two output files
    output1 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    output2 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")

    # For role 1: mute odd indices (0, 2, 4, ...), keep even indices (1, 3, 5, ...)
    # For role 2: mute even indices (1, 3, 5, ...), keep odd indices (0, 2, 4, ...)

    # Determine which indices belong to which role
    role1_indices = []
    role2_indices = []

    for idx, utterance in enumerate(dialog):
        ref_voice = utterance['ref_voice']
        if role_map[ref_voice] == 1:
            role1_indices.append(idx)
        else:
            role2_indices.append(idx)

    # Create output1: mute role 2 (keep role 1)
    merge_audio_files(temp_files, output1, mute_indices=set(role2_indices))
    pad_audio_file(output1, pad_seconds)

    # Free memory before second merge (important for large batches)
    gc.collect()

    # Create output2: mute role 1 (keep role 2)
    merge_audio_files(temp_files, output2, mute_indices=set(role1_indices))
    pad_audio_file(output2, pad_seconds)

    # Clean up temp files
    for temp_file in temp_files:
        Path(temp_file).unlink()

    # Final memory cleanup after processing all utterances
    del temp_files, role1_indices, role2_indices
    clear_gpu_memory(tts)

    print(f"Successfully processed dialog with {total_utterances} utterances", file=sys.stderr)

    return {
        'audio_file1': output1,
        'audio_file2': output2
    }


def handle_questions(tts, data, output_dir, pad_seconds: float):
    """
    Handle questions mode (Q&A pairs).

    Expected JSON structure:
    {
        "questions": [
            {
                "question": {
                    "text": "question text",
                    "ref_voice": "path/to/voice.wav",
                    "emotion_sample": "emotion description",  # optional
                    "ref_emotion_voice": "path/to/emotion.wav"  # optional
                },
                "answer": {
                    "text": "answer text",
                    "ref_voice": "path/to/voice.wav",
                    "emotion_sample": "emotion description",  # optional
                    "ref_emotion_voice": "path/to/emotion.wav"  # optional
                }
            },
            ...
        ]
    }

    Creates two audio files:
    - audio_file1: Contains only questions (answers are muted/silent)
    - audio_file2: Contains only answers (questions are muted/silent)

    Args:
        tts: IndexTTS2 model instance
        data (dict): Input data containing questions array
        output_dir (str): Directory where output audio will be saved

    Returns:
        dict: {'audio_file1': path_to_questions_audio, 'audio_file2': path_to_answers_audio}
    """
    questions = data['questions']
    total_pairs = len(questions)
    print(f"Processing {total_pairs} Q&A pairs...", file=sys.stderr)

    question_files = []
    answer_files = []

    for idx, qa_pair in enumerate(questions, 1):
        question_data = qa_pair['question']
        answer_data = qa_pair['answer']

        # Progress logging for large batches
        if total_pairs > 10 and idx % 10 == 0:
            print(f"Progress: {idx}/{total_pairs} Q&A pairs processed ({idx*100//total_pairs}%)", file=sys.stderr)

        # Generate question audio
        q_temp = str(Path(output_dir) / f"temp_q_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            question_data['text'],
            question_data.get('emotion_sample', ''),
            question_data['ref_voice'],
            q_temp,
            ref_emotion_voice=question_data.get('ref_emotion_voice') or question_data['ref_voice'],
            verbose=False,
            pad_seconds=0.0,
        )
        question_files.append(q_temp)

        # Aggressively clear GPU memory to prevent VRAM accumulation
        clear_gpu_memory(tts)

        # Generate answer audio
        a_temp = str(Path(output_dir) / f"temp_a_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            answer_data['text'],
            answer_data.get('emotion_sample', ''),
            answer_data['ref_voice'],
            a_temp,
            ref_emotion_voice=answer_data.get('ref_emotion_voice') or answer_data['ref_voice'],
            verbose=False,
            pad_seconds=0.0,
        )
        answer_files.append(a_temp)

        # Aggressively clear GPU memory to prevent VRAM accumulation
        clear_gpu_memory(tts)

    # Interleave questions and answers
    all_files = []
    for q, a in zip(question_files, answer_files):
        all_files.append(q)
        all_files.append(a)

    # Create two output files
    output1 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    output2 = str(Path(output_dir) / f"{uuid.uuid4()}.wav")

    # Output1: full audio with answers muted (keep questions)
    answer_indices = [i for i in range(len(all_files)) if i % 2 == 1]
    merge_audio_files(all_files, output1, mute_indices=set(answer_indices))
    pad_audio_file(output1, pad_seconds)

    # Free memory before second merge (important for large batches)
    gc.collect()

    # Output2: full audio with questions muted (keep answers)
    question_indices = [i for i in range(len(all_files)) if i % 2 == 0]
    merge_audio_files(all_files, output2, mute_indices=set(question_indices))
    pad_audio_file(output2, pad_seconds)

    # Clean up temp files
    for temp_file in all_files:
        Path(temp_file).unlink()

    # Final memory cleanup after processing all Q&A pairs
    del all_files, question_files, answer_files
    clear_gpu_memory(tts)

    print(f"Successfully processed all {total_pairs} Q&A pairs", file=sys.stderr)

    return {
        'audio_file1': output1,
        'audio_file2': output2
    }


def handle_segments(tts, data, output_dir, pad_seconds: float):
    """
    Handle segments mode - multiple segments with shared ref_voice returning individual files.

    Expected JSON structure:
    {
        "ref_voice": "path/to/voice.wav",
        "segments": [
            {
                "text": "line text",
                "emotion": "emotion_name",  # required
                "emotion_sample": "emotion description",  # required
                "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
            },
            ...
        ]
    }

    Args:
        tts: IndexTTS2 model instance
        data (dict): Input data containing ref_voice and segments array
        output_dir (str): Directory where output audio will be saved

    Returns:
        dict: {'audio_files': [paths_to_generated_segments]}
    """
    segments = data['segments']
    total_segments = len(segments)
    ref_voice = data['ref_voice']
    print(f"Processing {total_segments} segments with single voice...", file=sys.stderr)

    audio_files = []

    for idx, segment in enumerate(segments, 1):
        text = segment['text']
        emotion = str(segment.get('emotion') or '').strip()
        emotion_sample = str(segment.get('emotion_sample') or '').strip()
        ref_emotion_voice = segment.get('ref_emotion_voice') or ref_voice  # Optional: defaults to ref_voice

        if not str(text or '').strip():
            raise ValueError(f"Segment {idx} missing text")
        if not emotion:
            raise ValueError(f"Segment {idx} missing emotion")
        if not emotion_sample:
            raise ValueError(f"Segment {idx} missing emotion_sample")

        if total_segments > 20 and idx % 20 == 0:
            print(f"Progress: {idx}/{total_segments} segments processed ({idx*100//total_segments}%)", file=sys.stderr)
        elif total_segments <= 20:
            print(f"Processing segment {idx}/{total_segments}: {text[:30]}...", file=sys.stderr)

        output_filename = str(Path(output_dir) / f"segment_{uuid.uuid4()}.wav")
        generate_audio(
            tts,
            text,
            emotion_sample,
            ref_voice,
            output_filename,
            ref_emotion_voice=ref_emotion_voice,
            verbose=False,
            pad_seconds=pad_seconds,
        )
        audio_files.append(output_filename)

        clear_gpu_memory(tts)

    print(f"Successfully processed all {total_segments} segments", file=sys.stderr)

    return {
        'audio_files': audio_files
    }


def handle_lines(tts, data, output_dir, pad_seconds: float):
    """
    Handle lines mode - multiple lines with emotions merged into single audio with silence.

    Expected JSON structure:
    {
        "ref_voice": "path/to/voice.wav",
        "lines": [
            {
                "text": "line text",
                "emotion": "emotion_name",  # required
                "emotion_sample": "emotion description",  # required
                "ref_emotion_voice": "path/to/emotion.wav"  # optional; defaults to ref_voice
            },
            ...
        ]
    }

    All lines use the same ref_voice. Audio files are merged with 0.5 second silence between them.

    Args:
        tts: IndexTTS2 model instance
        data (dict): Input data containing ref_voice and lines array
        output_dir (str): Directory where output audio will be saved

    Returns:
        dict: {'audio_file': path_to_merged_audio}
    """
    lines = data['lines']
    total_lines = len(lines)
    ref_voice = data['ref_voice']
    print(f"Processing {total_lines} lines with single voice...", file=sys.stderr)

    temp_files = []

    # Generate audio for each line
    for idx, line in enumerate(lines, 1):
        text = line['text']
        emotion = str(line.get('emotion') or '').strip()
        emotion_sample = str(line.get('emotion_sample') or '').strip()
        ref_emotion_voice = line.get('ref_emotion_voice') or ref_voice  # Optional: defaults to ref_voice

        if not str(text or '').strip():
            raise ValueError(f"Line {idx} missing text")
        if not emotion:
            raise ValueError(f"Line {idx} missing emotion")
        if not emotion_sample:
            raise ValueError(f"Line {idx} missing emotion_sample")

        # Progress logging for large batches
        if total_lines > 20 and idx % 20 == 0:
            print(f"Progress: {idx}/{total_lines} lines processed ({idx*100//total_lines}%)", file=sys.stderr)
        elif total_lines <= 20:
            print(f"Processing line {idx}/{total_lines}: {text[:30]}...", file=sys.stderr)

        # Generate temporary audio file
        temp_filename = str(Path(output_dir) / f"temp_line_{uuid.uuid4()}.wav")

        generate_audio(
            tts,
            text,
            emotion_sample,
            ref_voice,
            temp_filename,
            ref_emotion_voice=ref_emotion_voice,
            verbose=False,
            pad_seconds=0.0,
        )
        temp_files.append(temp_filename)

        # Aggressively clear GPU memory to prevent VRAM accumulation
        clear_gpu_memory(tts)

    # Merge all audio files with 0.5s silence between them
    output_file = str(Path(output_dir) / f"{uuid.uuid4()}.wav")
    merge_audio_files(temp_files, output_file, silence_duration=0.5)
    pad_audio_file(output_file, pad_seconds)

    # Clean up temp files
    for temp_file in temp_files:
        Path(temp_file).unlink()

    # Final memory cleanup after processing all lines
    del temp_files
    clear_gpu_memory(tts)

    print(f"Successfully processed all {total_lines} lines", file=sys.stderr)

    return {
        'audio_file': output_file
    }


def main():
    parser = argparse.ArgumentParser(description='TTS generation script')
    parser.add_argument('--json-str', required=True, help='JSON string input')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='Output directory for generated audio files')
    parser.add_argument('--pad-seconds', type=float, default=DEFAULT_SILENCE_PADDING, help='Seconds of silence to pad at start and end of each output audio file')
    args = parser.parse_args()

    try:
        # Parse JSON input
        data = json.loads(args.json_str)

        # Ensure output directory exists
        output_dir = Path(str(data.get('output_dir') or args.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize TTS model
        tts = init_tts()

        # Determine input mode and process
        if 'segments' in data:
            result = handle_segments(tts, data, str(output_dir), args.pad_seconds)
        elif 'lines' in data:
            result = handle_lines(tts, data, str(output_dir), args.pad_seconds)
        elif 'dialog' in data:
            result = handle_dialog(tts, data, str(output_dir), args.pad_seconds)
        elif 'questions' in data:
            result = handle_questions(tts, data, str(output_dir), args.pad_seconds)
        else:
            result = handle_single_text(tts, data, str(output_dir), args.pad_seconds)

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
