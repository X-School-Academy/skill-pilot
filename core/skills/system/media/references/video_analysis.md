# video_analysis

Analyze a video using AI vision model to answer questions or provide descriptions.

Args:
    prompt: Your question or request about the video (e.g., "What happens in this video?", "Describe the actions", "Count how many people appear", etc.)
    video_file: Local video file path or remote URL to analyze (supports MP4, AVI, MOV formats)
    frame_step: How many frames to skip between samples (1=analyze every frame, 16=analyze every 16th frame for faster processing)
    max_frames: Maximum number of frames to analyze (-1 means analyze all sampled frames)
    max_tokens: Maximum length of the analysis response in tokens (default: 2048)

Returns:
    Text response with the video analysis or answer to your question

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "video_analysis", "arguments": {}}'
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
    "frame_step": {
      "default": 16,
      "type": "integer"
    },
    "max_frames": {
      "default": -1,
      "type": "integer"
    },
    "max_tokens": {
      "default": 2048,
      "type": "integer"
    }
  },
  "required": [
    "prompt",
    "video_file"
  ],
  "type": "object"
}
```
