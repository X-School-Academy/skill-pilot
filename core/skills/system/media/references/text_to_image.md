# text_to_image

Generate an image from a text description using AI image generation.

Args:
    prompt: Detailed description of the image you want to create (describe subjects, style, colors, composition, mood, etc.)
    width: Width of the generated image in pixels (default: 624)
    height: Height of the generated image in pixels (default: 624)

Returns:
    Generated image as a URL in PNG or JPEG format

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_image", "arguments": {}}'
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
      "default": 624,
      "type": "integer"
    },
    "height": {
      "default": 624,
      "type": "integer"
    }
  },
  "required": [
    "prompt"
  ],
  "type": "object"
}
```
