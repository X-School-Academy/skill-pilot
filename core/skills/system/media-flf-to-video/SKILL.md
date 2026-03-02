---
name: media-flf-to-video
description: "Create a video by interpolating motion between two images (first and last frame)."
---

Args:
    prompt: Description of the transition and motion between the frames (e.g., "smooth transition", "person walks from position A to B", "camera pans", etc.)
    first_frame_image: Starting frame image file_id from /upload_file
    last_frame_image: Ending frame image file_id from /upload_file
    width: Width of the generated video in pixels (default: 768)
    height: Height of the generated video in pixels (default: 512)

Returns:
    Generated video as a URL interpolating between the two frames in MP4 format, no audio

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "flf_to_video", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "prompt": {
      "type": "string"
    },
    "first_frame_image": {
      "type": "string"
    },
    "last_frame_image": {
      "type": "string"
    },
    "width": {
      "default": 768,
      "type": "integer"
    },
    "height": {
      "default": 512,
      "type": "integer"
    }
  },
  "required": [
    "prompt",
    "first_frame_image",
    "last_frame_image"
  ],
  "type": "object"
}
```
