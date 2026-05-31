# Left Nav Map

Use this file as the feature index for Skill Pilot WebUI routing.

## Root App Shell Nav

These items are defined on the main WebUI home shell.

| Nav label | Route shape | Reference |
| --- | --- | --- |
| `New Session` | `/` | `home-views.md` |
| `Live Sessions` | `/terminals` | `terminal-shell.md` |
| `Learning` | `/courses` | `workspace-pages.md` |
| `Vibe Coding` | `/vibe-coding` | `workspace-pages.md` |
| `Research` | `/research` | `workspace-pages.md` |
| `Tasks` | `/tasks` | `workspace-pages.md` |
| `Development` | `/skill-pilot-development` | `workspace-pages.md` |
| `Dev Swarm` | `/dev-swarm` | `workspace-pages.md` |
| `Processes` | `/processes` | `home-views.md` |
| `Discord Bot` | `/discord-bot` | `home-views.md` |
| `Live Avatar` | `/live-avatar` | `workspace-pages.md` |
| `Security Cameras` | `/cameras` | `workspace-pages.md` |
| `Skills` | `/skills` | `home-views.md` |
| `Workflows` | `/workflows` | `workspace-pages.md` |
| `MCP Servers` | `/mcp-servers` | `home-views.md` |
| `Schedules` | `/schedules` | `home-views.md` |
| `Extensions` | `/extensions` | `home-views.md` |
| `AI & Security` | `/ai-security` | `home-views.md` |
| `Profile` | `/profile` | `home-views.md` |

## Routing Rule

- If the target item uses `/?view=...`, open the main WebUI URL and then navigate to that query-string view
- If the target item uses a dedicated path like `/tasks` or `/research`, open that path directly from the WebUI base URL
- For direct terminal-only pages without the left nav, do not use this map; use `terminal-shell.md` or `terminal-agent.md`
