## MCP Servers Management Screen

Replace the "MCP Servers" placeholder in the webui with a functional management screen.

### MCP Server List

- Show all MCP servers from `config/mcp.json5`
- Each entry displays: name, type (stdio / streamable-http / sse), whether it is a system server, whether it is disabled
- System servers do not allow editing or deletion

### Add / Edit MCP Server Form

- Type selector: stdio, streamable-http, sse
- Fields depend on the selected type:
  - **stdio**: command (text), args (list), env (key-value pairs)
  - **streamable-http**: url (text), headers (key-value pairs)
  - **sse**: url (text), headers (key-value pairs)
- Disabled toggle
- On save, update `config/mcp.json5`
- System servers cannot be edited or deleted

### Config File

- Path: `config/mcp.json5`
- Structure: `{ "mcpServers": { "<name>": { ...config } } }`
- Type mapping: `type: "http"` in the file means streamable-http in the UI; `type: "sse"` means SSE; no `type` field (or absent) with a `command` field means stdio
- `system: true` marks a server as system (read-only)
- `disabled: true` marks a server as disabled

### Extra
add a cli `core/bin/sync-mcp` point to core/engine/mcp/mcp_to_skills/sync.py
Once updated, invoke shells `core/bin/sync-mcp`, `core/bin/skill-verify`, `core/bin/skill-install` one by one

In the mcp server list's bottom, add a manual sync button, run the 3 clis one by one
