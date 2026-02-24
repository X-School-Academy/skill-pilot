---
name: dart-hover
description: "Get hover information at a given cursor position in a file. This can include documentation, type information, etc for the text at that position."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "hover", "arguments": {}}'
```

## Tool Description
Get hover information at a given cursor position in a file. This can include documentation, type information, etc for the text at that position.

## Arguments Schema
```json
{
  "type": "object",
  "properties": {
    "uri": {
      "type": "string",
      "description": "The URI of the file."
    },
    "line": {
      "type": "integer",
      "description": "The zero-based line number of the cursor position."
    },
    "column": {
      "type": "integer",
      "description": "The zero-based column number of the cursor position."
    }
  },
  "required": [
    "uri",
    "line",
    "column"
  ]
}
```
