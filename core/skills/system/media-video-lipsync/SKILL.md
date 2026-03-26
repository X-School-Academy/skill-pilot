---
name: media-video-lipsync
description: "Run the MuseTalk lip-sync CLI to align a reference video with a new audio track."
---

Args:
    audio_file: Local speech or singing audio file path or remote URL to drive the lip-sync.
    video_file: Input local video file path or remote URL whose lip movements should be updated.
    label: Optional identifier that is forwarded to the MuseTalk CLI for logging.
    pingpong: When true (default), mirror the input clip into a forward+reverse pingpong loop before lip-syncing.

Returns:
    Lip-synced video as a URL produced by MuseTalk.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_lipsync", "arguments": {}}'
```

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "audio_file": {
      "type": "string"
    },
    "video_file": {
      "type": "string"
    },
    "label": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "pingpong": {
      "default": true,
      "type": "boolean"
    }
  },
  "required": [
    "audio_file",
    "video_file"
  ],
  "type": "object"
}
```
