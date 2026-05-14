# Feature Retrieval Index: Explore and Showcases

## Retrieval Keywords

explore, showcase, showcases, explore page, template start, template status, explore template, skill-pilot explore, starter template, example project, explore-showcase-skill, new-skill-session

## Scope

- Listing available showcase/starter templates
- Starting a new session from a template
- Polling template start status
- Excludes: vibe coding projects (separate), course content (separate)

## Main Behavior

- `GET /api/explore/showcases` returns available showcase templates
- `POST /api/explore/template/start` starts a new session from a selected template
- `GET /api/explore/template/status` polls the template start progress

## Code Map

- `core/engine/routes.py` — `/api/explore/*` route handlers
- `core/development/explore-showcase-skill/` — explore showcase feature development docs
- `core/skills/system/new-skill-session/` — new session from template skill

## Search Commands

```bash
rg "api/explore" core/engine/routes.py -n
find core/development/explore-showcase-skill/ -type f
find core/skills/system/new-skill-session/ -type f
```

## Related Features

- `core/features/skill-agent-system.md`
- `core/features/vibe-coding-project-manager.md`

## Update Notes

- Template start is asynchronous; poll `/api/explore/template/status` with the returned ID
- Showcases are curated templates; add new ones by updating the showcases list in the route handler
