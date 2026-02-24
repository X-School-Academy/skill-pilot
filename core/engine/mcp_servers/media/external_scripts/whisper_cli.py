#!/media/frankhe/Data/miniconda3/envs/whisper/bin/python
import argparse
import json
import sys
import torch
import whisper


def transcribe_audio(audio_file, language=None, use_fp16=False):
    """Transcribe audio file and return word-level timestamps"""
    print(f"Loading Whisper model (fp16={use_fp16})...", file=sys.stderr)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load model with fp16 setting
    model = whisper.load_model("medium", device=device)

    print(f"Transcribing audio file: {audio_file}", file=sys.stderr)

    # Transcribe with word timestamps
    transcribe_options = {
        "word_timestamps": True,
        "verbose": True,
        "fp16": use_fp16 and device == "cuda"
    }

    if language:
        transcribe_options["language"] = language

    result = model.transcribe(audio_file, **transcribe_options)

    segments = []
    for seg in result.get("segments", []):
        segment = {}
        segment["text"] = seg.get("text", "").strip()
        segment["start"] = seg.get("start", 0.0)
        segment["end"] = seg.get("end", 0.0)
        segment["words"] = seg.get("words", [])
        segments.append(segment)

    print(f"Transcription complete. Found {len(segments)} segments.", file=sys.stderr)

    return segments


def main():
    parser = argparse.ArgumentParser(description='Whisper transcription with word timestamps')
    parser.add_argument('--json-str', required=True, help='JSON string input with audio_file, language, f16')
    args = parser.parse_args()

    try:
        # Parse JSON input
        data = json.loads(args.json_str)

        # Extract parameters
        audio_file = data.get('audio_file')
        language = data.get('language', 'en')
        use_fp16 = data.get('f16', True)

        if not audio_file:
            raise ValueError("Missing required parameter: audio_file")

        # Transcribe audio
        words_data = transcribe_audio(audio_file, language, use_fp16)

        # Output result in JSON format
        result = {
            'segments': words_data
        }
        print(f"<json-output>{json.dumps(result, ensure_ascii=False)}</json-output>")

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
