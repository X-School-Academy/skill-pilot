---
name: cameras-webrtc-offer
description: "Accept a WebRTC SDP offer from the WebUI, create the server-side"
---

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
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "cameras", "tool_name": "webrtc_offer", "arguments": {}}'
```

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
