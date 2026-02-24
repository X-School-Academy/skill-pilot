---
name: terminal-scp-download
description: "Start an asynchronous SFTP download from an SSH target to localPath."
---

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "terminal", "tool_name": "scp_download", "arguments": {}}'
```

## Tool Description
Start an asynchronous SFTP download from an SSH target to localPath.

## Arguments Schema
```json
{
  "properties": {
    "target": {
      "title": "Target",
      "type": "string"
    },
    "remotePath": {
      "title": "Remotepath",
      "type": "string"
    },
    "localPath": {
      "title": "Localpath",
      "type": "string"
    }
  },
  "required": [
    "target",
    "remotePath",
    "localPath"
  ],
  "title": "scp_downloadArguments",
  "type": "object"
}
```
