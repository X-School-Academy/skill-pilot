---
name: media-image-to-image
description: "Modify or transform an existing image based on text instructions using AI."
---

Args:
    prompt: Description of how you want to modify the image (e.g., "add flowers", "change to winter scene", "make it look vintage", etc.)
    image_file: Image file_id from /upload_file to modify (supports PNG, JPEG formats)

Returns:
    Modified image as a URL in PNG or JPEG format

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_to_image", "arguments": {}}'
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
    }
  },
  "required": [
    "prompt",
    "image_file"
  ],
  "type": "object"
}
```
