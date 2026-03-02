---
name: media-audio-segments
description: "Transcribe audio and return segments with timing information for understanding scene transitions."
---

This tool helps AI agents understand the timing and structure of audio content, which is crucial
for video editing tasks such as:
- Splitting narration into natural scene segments based on speech pauses
- Synchronizing video transitions with audio timing
- Aligning visual content with spoken content
- Creating captions or subtitles with accurate timestamps
- Planning video scene cuts at natural speech boundaries

Args:
    audio_file: Audio file_id from /upload_file to transcribe (supports MP3, WAV, M4A, etc.)
    language: Language code for transcription (default: "en"). Common codes: en, es, fr, de, it, pt, ru, ja, zh, ko
    use_fp16: Use FP16 precision for faster processing (default: True, requires CUDA)

Returns:
    List of segments, each containing:
    - text: The transcribed text for this segment
    - start: Start time of the segment in seconds (float)
    - end: End time of the segment in seconds (float)
    - words: List of word-level timestamps (each with 'word', 'start', 'end')

Example return value:
    [
        {
            "text": "Hello and welcome to this tutorial.",
            "start": 0.5,
            "end": 3.2,
            "words": [
                {"word": "Hello", "start": 0.5, "end": 0.9},
                {"word": "and", "start": 1.0, "end": 1.1},
                ...
            ]
        },
        {
            "text": "Today we'll be learning about video editing.",
            "start": 3.5,
            "end": 6.8,
            "words": [...]
        }
    ]

Use cases:
    - Find natural pauses between sentences to plan scene transitions
    - Synchronize video clips with specific parts of narration
    - Create dynamic captions that appear word-by-word
    - Split long videos into chapters based on topic changes
    - Identify timing for background music to avoid overlapping with speech

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "audio_segments", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "audio_file": {
      "type": "string"
    },
    "language": {
      "default": "en",
      "type": "string"
    }
  },
  "required": [
    "audio_file"
  ],
  "type": "object"
}
```
