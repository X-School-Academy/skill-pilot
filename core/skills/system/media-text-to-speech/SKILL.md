---
name: media-text-to-speech
description: "Generate speech audio from text using TTS model."
---

Args:
    text: The text content you want to convert into spoken words
    emotion: The emotional tone for the voice (neutral, happy, sad, angry, excited, calm, etc.)
    emotion_sample: Sentence showing the desired emotional delivery style (required)
    gender: The gender of the voice (male or female)
    age: Approximate age of the voice in years (affects voice characteristics)
    ref_voice: Audio file_id from /upload_file to use as reference for voice characteristics and timbre (required)
    ref_emotion_voice: Optional audio file_id from /upload_file to control emotional delivery;
                       when omitted/empty, defaults to ref_voice.

Returns:
    Generated speech audio as a URL in MP3 format

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_speech", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "text": {
      "type": "string"
    },
    "emotion": {
      "type": "string"
    },
    "emotion_sample": {
      "default": "",
      "type": "string"
    },
    "gender": {
      "default": "female",
      "type": "string"
    },
    "age": {
      "default": 30,
      "type": "integer"
    },
    "ref_voice": {
      "default": "",
      "type": "string"
    },
    "ref_emotion_voice": {
      "default": "",
      "type": "string"
    }
  },
  "required": [
    "text",
    "emotion"
  ],
  "type": "object"
}
```
