---
name: dart-set-widget-selection-mode
description: "Enables or disables widget selection mode in the active Flutter application. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "set_widget_selection_mode", "arguments": {}}'
```

## Tool Description
Enables or disables widget selection mode in the active Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "title": "Enable widget selection mode"
    }
  },
  "required": [
    "enabled"
  ]
}
```
