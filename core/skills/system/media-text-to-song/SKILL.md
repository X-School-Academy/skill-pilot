---
name: media-text-to-song
description: "Generate singing audio from lyrics with musical vocal delivery."
---

Args:
    lyrics: The song lyrics to be sung (can include multiple verses and chorus)
    ref_voice: Required local audio file path or remote URL to use as reference for the singing voice timbre and characteristics

Returns:
    Generated singing audio as a URL in MP3 format

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_song", "arguments": {}}'
```

## Arguments Schema
```json
{
  "additionalProperties": false,
  "properties": {
    "lyrics": {
      "type": "string"
    },
    "ref_voice": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "lyrics"
  ],
  "type": "object"
}
```
