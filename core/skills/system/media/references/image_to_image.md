# image_to_image

Modify or transform an existing image based on text instructions using AI.

Args:
    prompt: Description of how you want to modify the image (e.g., "add flowers", "change to winter scene", "make it look vintage", etc.)
    image_file: Local image file path or remote URL to modify (supports PNG, JPEG formats)

Returns:
    Modified image as a URL in PNG or JPEG format

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_image", "arguments": {}}'
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
    }
  },
  "required": [
    "prompt",
    "image_file"
  ],
  "type": "object"
}
```
