---
name: media-text-segments-to-speech
description: "Generate speech audio for multiple lines with per-line emotion control."
---

Args:
    segments: List of dicts with fields text, emotion, and emotion_sample (all required);
              Optionally include ref_emotion_voice per segment as a file_id from /upload_file;
              when omitted/empty, defaults to ref_voice.
    gender: The gender of the voice (male or female)
    age: Approximate age of the voice in years (affects voice characteristics)
    ref_voice: Audio file_id from /upload_file to use as reference for voice characteristics and timbre

Returns:
    List of generated speech audio segments as HTTP URLs (http://host:port/file/path) in WAV format

    Example:
    segments = [
        {
            "text": "Hi there! It is great to meet you.",
            "emotion": "happy",
            "emotion_sample": "I am so glad we finally get to meet in person!",
            "ref_emotion_voice": "file_id_from_upload"
        },
        {
            "text": "This is serious, so please pay attention.",
            "emotion": "serious",
            "emotion_sample": "This is serious, so please pay attention.",
            "ref_emotion_voice": "file_id_from_upload"
        }
    ]
    audio = await text_segments_to_speech(segments, gender="female", age=28, ref_voice="file_id_from_upload")

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_segments_to_speech", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "segments": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
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
    }
  },
  "required": [
    "segments"
  ],
  "type": "object"
}
```
