# resolve_workspace_symbol

Look up a symbol or symbols in all workspaces by name. Can be used to validate that a symbol exists or discover small spelling mistakes, since the search is fuzzy.

## Usage
```bash
core/bin/tool-cli request '{"server_id": "dart", "tool_name": "resolve_workspace_symbol", "arguments": {}}'
```
**Do not use any Python helper code to invoke the `core/bin/tool-cli` command. Run as shell command with arguments directly.**

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
