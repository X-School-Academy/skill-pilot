---
name: media-image-analysis
description: "Analyze an image using AI vision model to answer questions or provide descriptions."
---

Args:
    prompt: Your question or request about the image (e.g., "What objects are in this image?", "Describe the scene", "What color is the car?", etc.)
    image_file: Local image file path or remote URL to analyze (supports PNG, JPEG formats)
    max_tokens: Maximum length of the analysis response in tokens (default: 512)

Returns:
    Text response with the image analysis or answer to your question

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "image_analysis", "arguments": {}}'
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
    "max_tokens": {
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
