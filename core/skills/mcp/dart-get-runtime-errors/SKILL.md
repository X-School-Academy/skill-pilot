---
name: dart-get-runtime-errors
description: "Retrieves the most recent runtime errors that have occurred in the active Dart or Flutter application. Requires \"connect_dart_tooling_daemon\" to be successfully called first."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "get_runtime_errors", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**


## Tool Description
Retrieves the most recent runtime errors that have occurred in the active Dart or Flutter application. Requires "connect_dart_tooling_daemon" to be successfully called first.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "clearRuntimeErrors": {
      "type": "boolean",
      "title": "Whether to clear the runtime errors after retrieving them.",
      "description": "This is useful to clear out old errors that may no longer be relevant before reading them again."
    }
  }
}
```
