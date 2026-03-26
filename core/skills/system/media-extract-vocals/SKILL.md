---
name: media-extract-vocals
description: "Extract vocals from an audio file using Demucs source separation."
---

This tool uses AI to separate vocals from background music and other sounds in an audio file.
Perfect for:
- Creating karaoke/instrumental versions by removing vocals
- Isolating vocal tracks for remixing or analysis
- Cleaning up dialogue with background music
- Preparing audio for vocal processing or lip-sync
- Extracting singing or speech from mixed audio

Args:
    audio_file: Local audio file path or remote URL (supports MP3, WAV, FLAC, M4A, etc.)

Returns:
    Extracted vocals audio as a URL in WAV format

Note:
    This process may take a few minutes depending on the audio length and system performance.
    The returned file contains only the vocal parts of the audio.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "extract_vocals", "arguments": {}}'
```

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "audio_file": {
      "type": "string"
    }
  },
  "required": [
    "audio_file"
  ],
  "type": "object"
}
```
