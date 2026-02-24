## MCP Servers Management — Summary

### What Was Done

#### 1. CLI Script: `core/bin/sync-mcp`
- Created new executable script following the existing `skill-install` / `skill-verify` pattern
- Points to `core/engine/mcp/mcp_to_skills/sync.py`

#### 2. Backend: `core/engine/routes.py`
- Added config path constants (`_REPO_ROOT`, `_MCP_CONFIG_PATH`, `_MCP_SERVER_NAME_RE`, `_MCP_SYNC_SCRIPTS`)
- Added helper functions: `_read_mcp_config()`, `_write_mcp_config()`, `_infer_mcp_server_type()`
- **`GET /api/config/mcp-servers`** — lists all servers with inferred display types
- **`POST /api/config/mcp-servers`** — creates or updates a server (rejects system servers with 403)
- **`DELETE /api/config/mcp-servers/{name}`** — removes a server (rejects system servers with 403)
- **`POST /api/config/mcp-servers/sync`** — runs sync-mcp, skill-verify, skill-install sequentially, returns output

Type mapping: `type: "http"` in config → `"streamable-http"` in API; `type: "sse"` → `"sse"`; no type field → `"stdio"`

#### 3. Frontend: `core/webui/pages/index.tsx`
- Added `McpServer`, `McpFormData` interfaces and `EMPTY_MCP_FORM` constant
- Added state: `mcpServers`, `mcpEditing`, `mcpForm`, `mcpSaving`, `mcpSyncing`, `mcpSyncOutput`, `mcpError`
- Added `fetchMcpServers()` with auto-fetch when MCP Servers view activates
- **List view**: server cards with name, type/system/disabled badges, command/url detail line, Edit/Delete buttons (hidden for system)
- **Add/Edit form**: name, type selector, conditional fields (stdio: command/args/env; http/sse: url/headers), disabled toggle, Save/Cancel
- **Key-value editor**: inline rows for env variables and headers with add/remove
- **Sync Skills section**: button at bottom runs the 3 CLIs, shows output in a pre block
- Replaced `renderPlaceholder('MCP Servers')` with `renderMcpServersView()`

### Files Changed
| File | Change |
|------|--------|
| `core/bin/sync-mcp` | New CLI script |
| `core/engine/routes.py` | 4 new API endpoints + helpers |
| `core/webui/pages/index.tsx` | MCP Servers management view |

### Design Decisions
- Type mapping kept consistent with existing `config/mcp.json5` format (`"http"` in file = `"streamable-http"` in UI)
- System servers are display-only — no Edit/Delete buttons, POST rejects with 403
- Sync runs all 3 scripts sequentially; partial failure returns results collected so far
- Key-value editor uses simple inline inputs (no Mantine form components) for consistency with existing card-style UI
