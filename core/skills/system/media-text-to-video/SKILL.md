---
name: media-text-to-video
description: "Generate a video clip from a text description using AI video generation."
---

Args:
    prompt: Detailed description of the video scene you want to create (describe action, movement, subjects, environment, camera motion, etc.)
    width: Width of the generated video in pixels (default: 768)
    height: Height of the generated video in pixels (default: 512)

Returns:
    Generated video as a URL in MP4 format, no audio

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_video", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "prompt": {
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
    "prompt"
  ],
  "type": "object"
}
```
