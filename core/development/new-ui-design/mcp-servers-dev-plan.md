## MCP Servers Management — Dev Plan

### Files to Create
1. `core/bin/sync-mcp` — CLI script (same pattern as `skill-install`)

### Files to Modify
1. `core/engine/routes.py` — 4 new API endpoints
2. `core/webui/pages/index.tsx` — MCP Servers view replacing placeholder

---

### Step 1: Create `core/bin/sync-mcp`

Follow the exact pattern of `core/bin/skill-install`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"
exec uv --project core/engine run core/engine/mcp/mcp_to_skills/sync.py "$@"
```

Make executable with `chmod +x`.

---

### Step 2: Backend — `core/engine/routes.py`

Add a module-level constant for config path:

```python
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_CONFIG_PATH = _REPO_ROOT / "config" / "mcp.json5"
_MCP_SERVER_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
```

#### 2a) `GET /api/config/mcp-servers`

- Read `_MCP_CONFIG_PATH`, parse JSON
- Transform `mcpServers` dict into a list with `name` field added
- Infer display type: if `type == "http"` → `"streamable-http"`, if `type == "sse"` → `"sse"`, else `"stdio"`
- Return `{ "servers": [...] }`

#### 2b) `POST /api/config/mcp-servers`

- Body: `{ name, type, command?, args?, env?, url?, headers?, disabled? }`
- Validate name with `_MCP_SERVER_NAME_RE`
- If server exists and has `system: true` → 403
- Build config object based on type:
  - `stdio`: `{ command, args, env, disabled }` (omit url/headers/type)
  - `streamable-http`: `{ type: "http", url, headers, disabled }` (omit command/args/env)
  - `sse`: `{ type: "sse", url, headers, disabled }` (omit command/args/env)
- Preserve `system: true` if it was already set (shouldn't happen due to guard, but safe)
- Read current config, update entry, write back with `json.dumps(data, indent=2) + "\n"`

#### 2c) `DELETE /api/config/mcp-servers/{name}`

- Validate name
- If server has `system: true` → 403
- If server not found → 404
- Remove entry, write back

#### 2d) `POST /api/config/mcp-servers/sync`

- Run the 3 CLI scripts sequentially using `subprocess.run`:
  1. `core/bin/sync-mcp`
  2. `core/bin/skill-verify`
  3. `core/bin/skill-install`
- Run each from `_REPO_ROOT` as cwd
- Collect stdout/stderr from each
- If any fails, return partial results with the error
- Return `{ "status": "ok", "results": [ { "command": "...", "exit_code": 0, "output": "..." }, ... ] }`

---

### Step 3: Frontend — `core/webui/pages/index.tsx`

#### 3a) New types and state

```typescript
interface McpServer {
  name: string;
  type: string;       // "stdio" | "streamable-http" | "sse"
  system?: boolean;
  disabled?: boolean;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
}

interface McpFormData {
  name: string;
  type: string;
  command: string;
  args: string;          // newline-separated, converted on save
  env: [string, string][];
  url: string;
  headers: [string, string][];
  disabled: boolean;
}
```

New state variables:
- `mcpServers: McpServer[]`
- `mcpEditing: string | null` — `'__new__'` for add, server name for edit, `null` for list
- `mcpForm: McpFormData`
- `mcpSyncing: boolean`
- `mcpSyncOutput: string`

#### 3b) Replace placeholder

Change `case 'mcp-servers': return renderPlaceholder('MCP Servers')` to `return renderMcpServersView()`.

#### 3c) `renderMcpServersView()`

**When `mcpEditing` is null** — List view:
- Header: "MCP Servers" title + "Add Server" button + "Refresh" button
- Server rows (card style matching Processes view):
  - Left: name (bold), type badge, "system" badge if applicable, "disabled" badge if applicable
  - Right: "Edit" button + "Delete" button (both hidden if `system`)
- Bottom section: "Sync Skills" button
  - On click: POST `/api/config/mcp-servers/sync`
  - Show syncing spinner, then display output summary

**When `mcpEditing` is set** — Add/Edit form:
- Header: "Add MCP Server" or "Edit: {name}" + "Cancel" button
- Name input (disabled when editing existing, i.e. `mcpEditing !== '__new__'`)
- Type select: `stdio` | `streamable-http` | `sse`
- Conditional fields:
  - **stdio**: Command text input, Args textarea (one per line), Env key-value editor
  - **streamable-http / sse**: URL text input, Headers key-value editor
- Disabled checkbox
- "Save" button

**Key-value editor** (inline helper for env/headers):
- Render `pairs.map((pair, i) => [key input, value input, "x" remove button])`
- "Add" button appends `["", ""]`
- On save: filter out empty-key rows, convert to `Record<string, string>`

#### 3d) Data flow

- Fetch `GET /api/config/mcp-servers` on view mount and after save/delete
- Save: `POST /api/config/mcp-servers` → re-fetch → back to list
- Delete: `DELETE /api/config/mcp-servers/{name}` with confirm → re-fetch
- Sync: `POST /api/config/mcp-servers/sync` → show results

---

### Verification

1. Start engine and webui
2. Click "MCP Servers" in nav → verify all servers listed with correct badges
3. Verify system server ("terminal") has no Edit/Delete buttons
4. Edit a non-system server → Save → check `config/mcp.json5` updated
5. Add a new server → Save → verify appears in list and config
6. Delete a non-system server → verify removed
7. Click "Sync Skills" → verify the 3 scripts run and output is shown
8. Run `core/bin/sync-mcp` directly from terminal → verify it works
