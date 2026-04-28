# flf_to_video

Create a video by interpolating motion between two images (first and last frame).

Args:
    prompt: Description of the transition and motion between the frames (e.g., "smooth transition", "person walks from position A to B", "camera pans", etc.)
    first_frame_image: Starting frame local image file path or remote URL
    last_frame_image: Ending frame local image file path or remote URL
    width: Final width of the generated video in pixels (default: 1536)
    height: Final height of the generated video in pixels (default: 1024)

Returns:
    Generated video as a URL interpolating between the two frames in MP4 format, no audio

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "flf_to_video", "arguments": {}}'
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
    "first_frame_image": {
      "type": "string"
    },
    "last_frame_image": {
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
    "first_frame_image",
    "last_frame_image"
  ],
  "type": "object"
}
```
