# Feature Retrieval Index: Vibe Coding Project Manager

## Retrieval Keywords

vibe coding, vibe-coding, vibe coding project, create project, update request, issue report, vibe coding tree, vibe coding content, vibe coding save, vibe coding delete, vibe coding file, workspace/vibe-coding, vibe_coding, vibe-coding-dev, project from prompt

## Scope

- Vibe coding project lifecycle: create, update, delete, issue reporting
- Project file tree and content viewer in the web UI
- AI skill integration for code generation (`vibe-coding` skill)
- Excludes: task manager, research manager (separate features)

## Main Behavior

- `GET /api/vibe-coding/tree` returns project directory tree
- `GET /api/vibe-coding/projects` lists all vibe coding projects
- `GET /api/vibe-coding/latest` returns the most recently active project
- `GET /api/vibe-coding/content` returns file content within a project
- `POST /api/vibe-coding/save` saves content
- `POST /api/vibe-coding/create-project` creates a new project
- `POST /api/vibe-coding/create-update-request` creates an update request for an existing project
- `POST /api/vibe-coding/create-issue-report` files an issue report
- `POST /api/vibe-coding/delete` removes a project
- `GET /api/vibe-coding/file` serves a raw project file
- Projects stored under `workspace/vibe-coding/`

## Code Map

- `core/engine/routes.py` — `/api/vibe-coding/*` route handlers
- `core/webui/pages/vibe-coding/index.tsx` — vibe coding web UI page
- `core/skills/system/vibe-coding/` — vibe coding system skill
- `workspace/vibe-coding/` — project storage directory
- `core/workflows/vibe-coding-dev.json` — vibe coding workflow template

## Search Commands

```bash
rg "api/vibe-coding" core/engine/routes.py -n
find core/skills/system/vibe-coding/ -type f
find workspace/vibe-coding/ -maxdepth 2 -type d
rg "vibe.coding" core/webui/pages/ -l
```

## Related Features

- `core/features/task-manager.md`
- `core/features/research-manager.md`
- `core/features/workflow-runner-editor.md`
- `core/features/agent-cli.md`

## Update Notes

- `workspace/vibe-coding/` is user data; preserve on upgrades
- `create-project` and `create-update-request` trigger background skill runs; check session lifecycle
