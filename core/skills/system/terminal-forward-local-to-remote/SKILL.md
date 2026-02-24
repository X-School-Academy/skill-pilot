---
name: terminal-forward-local-to-remote
description: "Start an SSH remote port-forward from remotePort to localHost:localPort."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "forward_local_to_remote", "arguments": {}}'
```

## Tool Description
Start an SSH remote port-forward from remotePort to localHost:localPort.

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "title": "Target",
      "type": "string"
    },
    "localHost": {
      "title": "Localhost",
      "type": "string"
    },
    "localPort": {
      "title": "Localport",
      "type": "integer"
    },
    "remotePort": {
      "title": "Remoteport",
      "type": "integer"
    },
    "remoteHost": {
      "default": "127.0.0.1",
      "title": "Remotehost",
      "type": "string"
    }
  },
  "required": [
    "target",
    "localHost",
    "localPort",
    "remotePort"
  ],
  "title": "forward_local_to_remoteArguments",
  "type": "object"
}
```
