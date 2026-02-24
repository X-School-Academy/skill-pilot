---
name: terminal-list-sessions
description: "List terminal sessions currently tracked by this MCP server."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "list_sessions", "arguments": {}}'
```

## Tool Description
List terminal sessions currently tracked by this MCP server.

## Arguments Schema
```json
{
  "properties": {},
  "title": "list_sessionsArguments",
  "type": "object"
}
```
