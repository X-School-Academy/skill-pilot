---
name: terminal-forward-remote-to-local
description: "Start an SSH local port-forward from localPort to remoteHost:remotePort."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "forward_remote_to_local", "arguments": {}}'
```

## Tool Description
Start an SSH local port-forward from localPort to remoteHost:remotePort.

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "title": "Target",
      "type": "string"
    },
    "remoteHost": {
      "title": "Remotehost",
      "type": "string"
    },
    "remotePort": {
      "title": "Remoteport",
      "type": "integer"
    },
    "localPort": {
      "default": 0,
      "title": "Localport",
      "type": "integer"
    }
  },
  "required": [
    "target",
    "remoteHost",
    "remotePort"
  ],
  "title": "forward_remote_to_localArguments",
  "type": "object"
}
```
