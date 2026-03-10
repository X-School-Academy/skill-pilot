# Skills Management

## Brief

Skill catalog view for browsing installed skills, toggling them on or off, and viewing or editing skill content.

## User Value

- Makes the available agent capabilities visible from the UI.
- Helps users control which skills are active.
- Supports direct viewing and editing of skill instructions.

## Main Behavior

- Loads skill categories such as system, dev-swarm, third-party, and user.
- Persists enabled or disabled state for skills.
- Opens a skill in use, view, or edit mode.
- Reads and writes skill content through backend endpoints.
- Works together with MCP sync when new tool-derived skills are generated.

## Related Features

- `mcp-servers.md`
- `skill-pilot-development.md`
- `dev-swarm.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- `core/engine/mcp_servers/mcp_to_skills`
- Keywords: `fetchSkills`, `skillCategories`, `skillDisabled`, `skillSubScreen`, `skillActiveTab`
- API routes: `/api/config/skills`, `/api/config/skills/update`, `/api/config/skills/{category}/{name}/content`

