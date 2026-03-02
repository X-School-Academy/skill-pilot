---
name: media-text-to-song
description: "Generate singing audio from lyrics with musical vocal delivery."
---

Args:
    lyrics: The song lyrics to be sung (can include multiple verses and chorus)
    emotion: The emotional style for the singing performance (calm, energetic, melancholic, joyful, etc.)
    emotion_sample: Optional sentence or audio file describing the singing style and emotional expression (use a declarative sentence, not a command)
    ref_voice: Optional audio file_id from /upload_file to use as reference for the singing voice timbre and characteristics

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
  "properties": {
    "lyrics": {
      "type": "string"
    },
    "emotion": {
      "default": "calm",
      "type": "string"
    },
    "emotion_sample": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null
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
