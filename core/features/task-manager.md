# Feature Retrieval Index: Task Manager

## Retrieval Keywords

task manager, tasks, task tree, task create, task save, task delete, task content, task file, workspace tasks, task automation, tasks API, task agent, tasks page, workspace/tasks

## Scope

- Task creation, editing, saving, and deletion under `workspace/tasks/`
- Task tree navigation and content viewing in the web UI
- AI-driven task automation delegation
- Excludes: vibe-coding projects (separate feature), research topics (separate feature)

## Main Behavior

- `GET /api/tasks/tree` returns the task directory tree
- `GET /api/tasks/latest` returns the most recently modified task
- `GET /api/tasks/content` returns task markdown content
- `POST /api/tasks/save` writes task content
- `POST /api/tasks/create` creates a new task entry
- `POST /api/tasks/delete` removes a task
- `GET /api/tasks/file` serves a raw task file
- Tasks are stored as files under `workspace/tasks/`

## Code Map

- `core/engine/routes.py` — `/api/tasks/*` route handlers
- `core/webui/pages/tasks/index.tsx` — tasks web UI page
- `workspace/tasks/` — task storage directory

## Search Commands

```bash
rg "api/tasks" core/engine/routes.py -n
grep -r "workspace/tasks" core/ --include="*.py" -l
rg "tasks" core/webui/pages/tasks/ -l
```

## Related Features

- `core/features/vibe-coding-project-manager.md`
- `core/features/research-manager.md`
- `core/features/file-manager.md`

## Update Notes

- Task files follow the same directory layout convention as vibe-coding and research
- `workspace/tasks/` is user data; back up before destructive migrations
