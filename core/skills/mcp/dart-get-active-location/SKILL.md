---
name: dart-get-active-location
description: "Retrieves the current active location (e.g., cursor position) in the connected editor. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_active_location", "arguments": {}}'
```

## Tool Description
Retrieves the current active location (e.g., cursor position) in the connected editor. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object"
}
```
