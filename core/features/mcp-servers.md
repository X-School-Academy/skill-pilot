# MCP Servers

## Brief

Management surface for configured MCP servers, including transport settings and skill-sync operations.

## User Value

- Centralizes MCP server definitions used by the engine.
- Supports both local command-based and remote URL-based servers.
- Connects server config changes to generated skill updates.

## Main Behavior

- Lists configured MCP servers with enabled or disabled state.
- Adds or edits `stdio`, `sse`, or `http` server definitions.
- Supports command, args, env vars, URL, and headers based on server type.
- Deletes server configs from the UI.
- Runs a sync action to refresh skills derived from MCP tools.

## Related Features

- `skills-management.md`
- `extensions.md`
- `ai-and-security.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- `core/engine/mcp_servers/mcp_to_skills`
- Keywords: `fetchMcpServers`, `mcpStartEdit`, `mcpStartAdd`, `mcpSave`, `mcpDelete`, `mcpSync`, `McpFormData`
- API routes: `/api/config/mcp-servers`, `/api/config/mcp-servers/{name}`, `/api/config/mcp-servers/sync`

