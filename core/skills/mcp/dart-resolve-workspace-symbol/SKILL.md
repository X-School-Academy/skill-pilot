---
name: dart-resolve-workspace-symbol
description: "Look up a symbol or symbols in all workspaces by name. Can be used to validate that a symbol exists or discover small spelling mistakes, since the search is fuzzy."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "resolve_workspace_symbol", "arguments": {}}'
```

## Tool Description
Look up a symbol or symbols in all workspaces by name. Can be used to validate that a symbol exists or discover small spelling mistakes, since the search is fuzzy.

## Arguments Schema
```json
{
  "type": "object",
  "description": "Returns all close matches to the query, with their names and locations. Be sure to check the name of the responses to ensure it looks like the thing you were searching for.",
  "properties": {
    "query": {
      "type": "string",
      "description": "Queries are matched based on a case-insensitive partial name match, and do not support complex pattern matching, regexes, or scoped lookups."
    }
  },
  "required": [
    "query"
  ]
}
```
