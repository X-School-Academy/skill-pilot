---
name: media-image-to-video
description: "Animate a static image into a video using AI to add motion and life."
---

Args:
    prompt: Description of how the image should be animated (e.g., "camera slowly zooms in", "trees sway in the wind", "person walks forward", etc.)
    image_file: Static image file_id from /upload_file to animate (supports PNG, JPEG formats)
    width: Width of the generated video in pixels (default: 768)
    height: Height of the generated video in pixels (default: 512)

Returns:
    Generated animated video as a URL in MP4 format, no audio

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_video", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "prompt": {
      "type": "string"
    },
    "image_file": {
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
    "image_file"
  ],
  "type": "object"
}
```
