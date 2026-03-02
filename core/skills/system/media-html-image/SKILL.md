---
name: media-html-image
description: "Create static html/css style image, transparent text overlay for video, and video thumbnail image."
---

Args:
    html_file: HTML file_id from /upload_file to render.
    width: Fallback viewport width (px) if CSS variables are not present.
    height: Fallback viewport height (px) if CSS variables are not present.
    transparent: When true, omit the page background for a transparent overlay image.

Returns:
    Captured image as a URL in PNG format.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "html_image", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "html_file": {
      "type": "string"
    },
    "width": {
      "type": "integer"
    },
    "height": {
      "type": "integer"
    },
    "transparent": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "html_file",
    "width",
    "height"
  ],
  "type": "object"
}
```
