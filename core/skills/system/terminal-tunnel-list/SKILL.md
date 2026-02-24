---
name: terminal-tunnel-list
description: "List all active SSH tunnels managed by this server."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "tunnel_list", "arguments": {}}'
```

## Tool Description
List all active SSH tunnels managed by this server.

## Arguments Schema
```json
{
  "properties": {},
  "title": "tunnel_listArguments",
  "type": "object"
}
```
