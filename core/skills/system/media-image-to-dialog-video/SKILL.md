---
name: media-image-to-dialog-video
description: "Generate two synchronized talking-head videos (one per dialog role) from a single portrait."
---

Args:
    prompt: Required guidance for the animation style and expressions.
    image_file: Local image file path or remote URL that will be re-animated for both roles.
    audio_file_one: Local audio file path or remote URL for the first role (left/top speaker by default).
    audio_file_two: Local audio file path or remote URL for the second role.
    width: Final width of each generated video.
    height: Final height of each generated video.
    reverse_order: Swap which audio drives the first/second split outputs (mirrors GPU worker toggle).
    max_frames: Maximum number of frames to render before stopping.

Returns:
    Dictionary with `split_one_video` and `split_two_video` as HTTP URLs (http://host:port/file/path).

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_dialog_video", "arguments": {}}'
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
    "audio_file_one": {
      "type": "string"
    },
    "audio_file_two": {
      "type": "string"
    },
    "width": {
      "default": 896,
      "type": "integer"
    },
    "height": {
      "default": 896,
      "type": "integer"
    },
    "reverse_order": {
      "default": false,
      "type": "boolean"
    },
    "max_frames": {
      "default": 450,
      "type": "integer"
    }
  },
  "required": [
    "prompt",
    "image_file",
    "audio_file_one",
    "audio_file_two"
  ],
  "type": "object"
}
```
