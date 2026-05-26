# Feature Retrieval Index: Config, Settings, MCP Servers, and Skills Management

## Retrieval Keywords

config, settings, settings.json5, env safeguard, profile, timezones, MCP servers, MCP config, skills config, installed skills, update skill, extensions, skill content, default provider, ai_providers, routes_config, config page, keys-safe-guard, sync-mcp, skill-install

## Scope

- Reading and writing `config/settings.json5`
- Environment variable safeguard status
- User profile management
- MCP server configuration (list, add, delete, sync)
- Skill content viewing and editing, installed skills listing
- Extension management (list, action)
- AI provider default configuration
- Excludes: LLM provider runtime (see llm-ai-chat feature), prompt inference (see agent-cli feature)

## Main Behavior

- `GET /api/config/settings` and `POST /api/config/settings` read/write settings
- `GET /api/config/env-safeguard-status` checks key safety status
- `GET /api/config/profile` and `POST /api/config/profile` manage user profile
- `GET /api/config/timezones` returns available timezones
- `GET /api/config/mcp-servers`, `POST /api/config/mcp-servers`, `DELETE /api/config/mcp-servers/{name}` manage MCP entries
- `POST /api/config/mcp-servers/sync` syncs MCP config to agents
- `GET /api/config/skills` lists available skills; `/installed` lists installed ones
- `POST /api/config/skills/update` updates a skill
- `GET /api/config/extensions` and `POST /api/config/extensions/action` manage extensions
- `GET /api/config/skills/{category}/{name}/content` and `POST` read/write skill content
- `POST /api/config/default-provider` sets the default AI provider
- CLI: `core/bin/sync-mcp`, `core/bin/skill-install`, `core/bin/keys-safe-guard`

## Code Map

- `core/engine/routes_config.py` — all `/api/config/*` route handlers
- `core/engine/settings.py` — settings file access, runtime mode, service config
- `core/engine/safe_dotenv/` — environment variable safeguard
- `core/bin/sync-mcp` — MCP sync CLI
- `core/bin/skill-install` — skill install CLI
- `core/bin/keys-safe-guard` — key safeguard CLI

## Search Commands

```bash
rg "api/config" core/engine/routes_config.py -n
cat core/engine/settings.py | head -80
find core/engine/safe_dotenv/ -type f
find core/bin/sync-mcp -o -find core/bin/skill-install 2>/dev/null
```

## Related Features

- `core/features/agent-cli.md`
- `core/features/llm-ai-chat.md`
- `core/features/mcp-terminal-server.md`

## Update Notes

- `config/settings.json5` uses JSON5 format; parsed by `core/engine/json5_io.py`
- `config/.env` is protected by `keys-safe-guard`; never expose in API responses
- MCP sync updates agent config files (`.claude/settings.json`, `.gemini/settings.json`, etc.)
