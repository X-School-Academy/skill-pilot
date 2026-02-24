---
name: dart-hot-reload
description: "Performs a hot reload of the active Flutter application. This is to apply the latest code changes to the running application. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "hot_reload", "arguments": {}}'
```

## Tool Description
Performs a hot reload of the active Flutter application. This is to apply the latest code changes to the running application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "clearRuntimeErrors": {
      "type": "boolean",
      "title": "Whether to clear runtime errors before hot reloading.",
      "description": "This is useful to clear out old errors that may no longer be relevant."
    }
  },
  "required": []
}
```
