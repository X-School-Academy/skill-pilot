---
name: media-video-upscale
description: "Upscale video size to 2X and restore face in the video."
---

Args:
    video_file: Local video file path or remote URL for face restore and upscale.

Returns:
    Refined 2x upscaled video as a local MP4 file path.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_upscale", "arguments": {}}'
```

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "video_file": {
      "type": "string"
    }
  },
  "required": [
    "video_file"
  ],
  "type": "object"
}
```
