# Feature Retrieval Index: Research Manager

## Retrieval Keywords

research, research topic, research manager, research tree, research content, research save, research delete, research multi-agent, deep research, workspace/research, refine-research-requirement, merge-research-results, research workflow

## Scope

- Research topic creation, editing, saving, deletion under `workspace/research/`
- Research file tree and content viewer
- AI-driven multi-agent deep research integration
- Excludes: task manager, vibe coding (separate features)

## Main Behavior

- `GET /api/research/tree` returns research directory tree
- `GET /api/research/latest` returns most recently modified research topic
- `GET /api/research/content` returns research topic content
- `POST /api/research/save` saves research content
- `POST /api/research/create-topic` creates a new research topic
- `POST /api/research/delete` removes a research topic
- `GET /api/research/file` serves a raw research file
- Research stored under `workspace/research/`

## Code Map

- `core/engine/routes.py` — `/api/research/*` route handlers
- `core/webui/pages/research/index.tsx` — research web UI page
- `core/skills/system/deep-research/` — deep research skill
- `core/skills/system/refine-research-requirement/` — research requirement refinement skill
- `core/skills/system/merge-research-results/` — multi-result merge skill
- `core/workflows/research-multi-agent.json` — multi-agent research workflow
- `workspace/research/` — research storage directory

## Search Commands

```bash
rg "api/research" core/engine/routes.py -n
find core/skills/system/deep-research/ -type f
find workspace/research/ -maxdepth 2 -type d 2>/dev/null
rg "research" core/webui/pages/research/ -l
```

## Related Features

- `core/features/task-manager.md`
- `core/features/workflow-runner-editor.md`
- `core/features/agent-cli.md`

## Update Notes

- `workspace/research/` is user data; preserve on upgrades
- Multi-agent workflow in `research-multi-agent.json` coordinates `deep-research` and `merge-research-results` skills
