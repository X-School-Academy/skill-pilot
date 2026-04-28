# webrtc_ice_candidate

Relay a WebRTC ICE candidate from the WebUI to the server peer connection.

Args:
    candidate: The ICE candidate string (e.g. "candidate:...").
    sdp_mid: The m-line identifier (sdpMid) of the ICE candidate.
    sdp_mline_index: The m-line index (sdpMLineIndex) of the candidate.

Returns:
    JSON string with key "status": "ok".

## Usage
```bash
core/bin/tool-cli request '{"server_id": "cameras", "tool_name": "webrtc_ice_candidate", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "properties": {
    "candidate": {
      "title": "Candidate",
      "type": "string"
    },
    "sdp_mid": {
      "default": "",
      "title": "Sdp Mid",
      "type": "string"
    },
    "sdp_mline_index": {
      "default": 0,
      "title": "Sdp Mline Index",
      "type": "integer"
    }
  },
  "required": [
    "candidate"
  ],
  "title": "webrtc_ice_candidateArguments",
  "type": "object"
}
```
