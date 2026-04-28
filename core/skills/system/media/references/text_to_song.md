# text_to_song

Generate singing audio from lyrics with musical vocal delivery.

Args:
    lyrics: The song lyrics to be sung (can include multiple verses and chorus)
    ref_voice: Required local audio file path or remote URL to use as reference for the singing voice timbre and characteristics

Returns:
    Generated singing audio as a URL in MP3 format

## Usage
```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "text_to_song", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

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
