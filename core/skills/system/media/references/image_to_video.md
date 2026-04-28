# image_to_video

Animate a static image into a video using AI to add motion and life.

Args:
    prompt: Description of how the image should be animated (e.g., "camera slowly zooms in", "trees sway in the wind", "person walks forward", etc.)
    image_file: Local image file path or remote URL to animate (supports PNG, JPEG formats)
    width: Final width of the generated video in pixels (default: 1536)
    height: Final height of the generated video in pixels (default: 1024)

Returns:
    Generated animated video as a URL in MP4 format, no audio

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_video", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

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
    "width": {
      "default": 1536,
      "type": "integer"
    },
    "height": {
      "default": 1024,
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
