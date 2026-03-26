---
name: live-tts-text-to-audio
description: "Convert text to audio and play it completely before returning."
---

Args:
    text: The text to convert to speech.

Returns:
    Status message indicating completion or error.

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "live-tts", "tool_name": "text_to_audio", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Arguments Schema
```json
{
  "properties": {
    "text": {
      "title": "Text",
      "type": "string"
    }
  },
  "required": [
    "text"
  ],
  "title": "text_to_audioArguments",
  "type": "object"
}
```
