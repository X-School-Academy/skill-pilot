# video_to_talk_video

Create a talking or singing video from an existing clip synchronized with audio.

Args:
    prompt: Optional guidance for the video generation style (e.g., "natural expression", "animated talking", "expressive singing", "energetic performance", etc.)
    video_file: Source local video file path or remote URL whose subject will be reanimated to match the audio.
    audio_file: Local speech or singing audio file path or remote URL that the face will be synchronized to (supports MP3, WAV formats)
    width: Final width of the generated video in pixels (default: 896)
    height: Final height of the generated video in pixels (default: 896)
    pingpong: When true (default), mirror the input clip into a forward+reverse pingpong loop before processing

Returns:
    Generated lip-synced video as a URL in MP4 format with audio, max 3 minutes

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_to_talk_video", "arguments": {}}'
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
    "video_file": {
      "type": "string"
    },
    "audio_file": {
      "type": "string"
    },
    "width": {
      "default": 896,
      "type": "integer"
    },
    "height": {
      "default": 896,
      "type": "integer"
    },
    "pingpong": {
      "default": true,
      "type": "boolean"
    }
  },
  "required": [
    "prompt",
    "video_file",
    "audio_file"
  ],
  "type": "object"
}
```
