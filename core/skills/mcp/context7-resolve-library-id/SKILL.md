---
name: context7-resolve-library-id
description: "Resolve a package or product name to the best matching Context7 library ID before calling query-docs."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "context7", "tool_name": "resolve-library-id", "arguments": {}}'
```

## Tool Description
Resolve a package or product name to the best matching Context7 library ID before calling query-docs.

## Arguments Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The question or task you need help with. This is used to rank library results by relevance to what the user is trying to accomplish. The query is sent to the Context7 API for processing. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query."
    },
    "libraryName": {
      "type": "string",
      "description": "Library name to search for and retrieve a Context7-compatible library ID."
    }
  },
  "required": [
    "query",
    "libraryName"
  ]
}
```
