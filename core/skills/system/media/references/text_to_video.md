# text_to_video

Generate a video clip from a text description using AI video generation.

Args:
    prompt: Detailed description of the video scene you want to create (describe action, movement, subjects, environment, camera motion, etc.)
    width: Final width of the generated video in pixels (default: 1536)
    height: Final height of the generated video in pixels (default: 1024)

Returns:
    Generated video as a URL in MP4 format, no audio

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_video", "arguments": {}}'
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
    "prompt"
  ],
  "type": "object"
}
```
