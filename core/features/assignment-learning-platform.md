# Feature Retrieval Index: Assignment and Learning Platform

## Retrieval Keywords

assignment, learning platform, Strapi, course content, assignment activity, submit assignment, assignment-last-step, assignment-web-url, tikzjax, rest/assignment, strapi4, course list, course material, embedded course, dev-swarm courses

## Scope

- REST endpoints for assignment tracking (last step, web URL, activity, submission)
- TikzJax rendering for course mathematical diagrams
- Strapi4-backed course content management
- Embedded course viewer in the web UI
- Excludes: locally generated AI courses (see `course-creator.md`)

## Main Behavior

- `POST /rest/assignment-last-step` records the last completed assignment step
- `POST /rest/assignment-web-url` records the web URL for an assignment
- `POST /rest/assignment-activity` logs assignment activity
- `POST /rest/submit-assignment` submits an assignment
- `POST /rest/tikzjax` renders TikZ diagrams to SVG/PNG
- Strapi4 integration provides CMS-backed course content
- Embedded viewer at `/embedded` pages

## Code Map

- `core/engine/routes_integrations.py` — `/rest/assignment-*`, `/rest/tikzjax` route handlers
- `core/engine/strapi4/` — Strapi4 CMS client
- `core/webui/pages/embedded/` — embedded course viewer pages
- `core/webui/pages/dev-swarm/` — dev swarm learning UI
- `core/webui/components/blocks/` — course content block renderers
- `core/webui/features/assignment/assignmentAPI.ts` — assignment API client
- `core/webui/features/assignment/assignmentSlice.ts` — Redux slice for assignment state

## Search Commands

```bash
rg "rest/assignment" core/engine/routes_integrations.py -n
find core/engine/strapi4/ -type f
rg "assignment" core/webui/features/assignment/ -l
find core/webui/pages/embedded/ -type f
```

## Related Features

- `core/features/course-creator.md`
- `core/features/llm-ai-chat.md`

## Update Notes

- Strapi4 connection URL and API key must be configured in `config/.env` or `settings.json5`
- TikzJax rendering requires LaTeX dependencies on the server
