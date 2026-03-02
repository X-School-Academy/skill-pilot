---
name: media-video-to-talk-video
description: "Create a talking or singing video from an existing clip synchronized with audio."
---

Args:
    prompt: Optional guidance for the video generation style (e.g., "natural expression", "animated talking", "expressive singing", "energetic performance", etc.)
    video_file: Source video file_id from /upload_file whose subject will be reanimated to match the audio.
    audio_file: Speech or singing audio file_id from /upload_file that the face will be synchronized to (supports MP3, WAV formats)
    width: Width of the generated video in pixels (default: 448)
    height: Height of the generated video in pixels (default: 448)
    upscale: When true (default), automatically upscale the generated video before returning
    pingpong: When true (default), mirror the input clip into a forward+reverse pingpong loop before processing

Returns:
    Generated lip-synced video as a URL in MP4 format with audio, max 3 minutes

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_to_talk_video", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "prompt": {
      "type": "string"
    },
    "video_file": {
      "type": "string"
    },
    "audio_file": {
      "type": "string"
    },
    "width": {
      "default": 448,
      "type": "integer"
    },
    "height": {
      "default": 448,
      "type": "integer"
    },
    "upscale": {
      "default": true,
      "type": "boolean"
    },
    "pingpong": {
      "default": true,
      "type": "boolean"
    }
  },
  "required": [
    "prompt",
    "video_file",
    "audio_file"
  ],
  "type": "object"
}
```
