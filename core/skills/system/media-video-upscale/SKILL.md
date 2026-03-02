---
name: media-video-upscale
description: "Upscale and enhance a video using the ComfyUI upscale workflow."
---

Args:
    video_file: Video file_id from /upload_file to upscale.

Returns:
    Upscaled video as a URL in MP4 format.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_upscale", "arguments": {}}'
```

## Arguments Schema
```json
{
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
