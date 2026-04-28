# text_to_speech

Generate speech audio from text using TTS model.

Args:
    text: The text content you want to convert into spoken words
    emotion: The emotional tone for the voice (neutral, happy, sad, angry, excited, calm, etc.)
    emotion_sample: Sentence showing the desired emotional delivery style (required)
    ref_voice: Local audio file path or remote URL to use as reference for voice characteristics and timbre (required)
    ref_emotion_voice: Optional local audio file path or remote URL to control emotional delivery;
                       when omitted/empty, defaults to ref_voice.

Returns:
    Generated speech audio as a URL in MP3 format

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_speech", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "additionalProperties": false,
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
