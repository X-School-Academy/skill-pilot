# webrtc_offer

Accept a WebRTC SDP offer from the WebUI, create the server-side
RTCPeerConnection with a data channel, and return the SDP answer.

After this call the WebUI should call webrtc_ice_candidate for each
ICE candidate, then open the data channel and use JSON messages for
all camera operations.

Args:
    sdp: The SDP offer string from the browser RTCPeerConnection.
    sdp_type: SDP type, usually "offer".

Returns:
    JSON string with keys "sdp" and "type" (the server SDP answer).

## Usage
```bash
core/bin/tool-cli request '{"server_id": "cameras", "tool_name": "webrtc_offer", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

## Arguments Schema
```json
{
  "properties": {
    "sdp": {
      "title": "Sdp",
      "type": "string"
    },
    "sdp_type": {
      "default": "offer",
      "title": "Sdp Type",
      "type": "string"
    },
    "candidates": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "title": "Candidates"
    }
  },
  "required": [
    "sdp"
  ],
  "title": "webrtc_offerArguments",
  "type": "object"
}
```
