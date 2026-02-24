---
name: dart-get-selected-widget
description: "Retrieves the selected widget from the active Flutter application. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_selected_widget", "arguments": {}}'
```

## Tool Description
Retrieves the selected widget from the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object"
}
```
