---
name: dart-get-widget-tree
description: "Retrieves the widget tree from the active Flutter application. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_widget_tree", "arguments": {}}'
```

## Tool Description
Retrieves the widget tree from the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object"
}
```
