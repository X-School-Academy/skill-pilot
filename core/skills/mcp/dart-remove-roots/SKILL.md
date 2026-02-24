---
name: dart-remove-roots
description: "Removes one or more project roots previously added via the add_roots tool."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "remove_roots", "arguments": {}}'
```

## Tool Description
Removes one or more project roots previously added via the add_roots tool.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "uris": {
      "type": "array",
      "description": "All the project roots to remove from this server.",
      "items": {
        "type": "string",
        "description": "The URIs of the roots to remove."
      }
    }
  }
}
```
