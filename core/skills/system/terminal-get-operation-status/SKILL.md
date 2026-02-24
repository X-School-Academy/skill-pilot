---
name: terminal-get-operation-status
description: "Get status for an async SCP or tunnel operation by operation ID."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "get_operation_status", "arguments": {}}'
```

## Tool Description
Get status for an async SCP or tunnel operation by operation ID.

## Arguments Schema
```json
{
  "properties": {
    "operationId": {
      "title": "Operationid",
      "type": "string"
    }
  },
  "required": [
    "operationId"
  ],
  "title": "get_operation_statusArguments",
  "type": "object"
}
```
