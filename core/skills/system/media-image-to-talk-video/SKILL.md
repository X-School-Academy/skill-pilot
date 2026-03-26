---
name: media-image-to-talk-video
description: "Create a single-person talking or singing video from a face image synchronized with audio."
---

Args:
    prompt: Optional guidance for the video generation style (e.g., "natural expression", "animated talking", "expressive singing", "energetic performance", etc.)
    image_file: Local face image file path or remote URL containing a face that will appear to speak or sing (headshot or portrait works best)
    audio_file: Local speech or singing audio file path or remote URL that the face will be synchronized to (supports MP3, WAV formats)
    width: Final width of the generated video in pixels (default: 896)
    height: Final height of the generated video in pixels (default: 896)

Returns:
    Generated lip-synced video as a URL in MP4 format with audio, max 3 minutes

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_talk_video", "arguments": {}}'
```

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "prompt": {
      "type": "string"
    },
    "image_file": {
      "type": "string"
    },
    "audio_file": {
      "type": "string"
    },
    "width": {
      "default": 896,
      "type": "integer"
    },
    "height": {
      "default": 896,
      "type": "integer"
    }
  },
  "required": [
    "prompt",
    "image_file",
    "audio_file"
  ],
  "type": "object"
}
```
