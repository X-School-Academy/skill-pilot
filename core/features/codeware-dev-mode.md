# Feature Retrieval Index: Codeware Dev Mode and Worktrees

## Retrieval Keywords

codeware, codeware about, codeware dev, dev mode, dev start, dev status, prod restart, worktrees, worktree create, worktree remove, workspace remote, codeware workspace, routes_codeware, worktree_utils, codeware branch, codeware version, codeware page, sp-webui-dev, sp-engine-dev

## Scope

- Codeware about information (version, remote)
- Development mode start and status for webui and engine
- Production server restart
- Git worktree create and remove for feature isolation
- Workspace remote configuration
- Excludes: feature lifecycle documents (see `skill-pilot-development-feature-lifecycle.md`), git operations (see `git-github` skill)

## Main Behavior

- `GET /api/codeware/about` returns version and remote info
- `POST /api/codeware/dev/start` starts dev mode (webui + engine in dev tmux sessions)
- `GET /api/codeware/dev/status` checks dev mode running state
- `POST /api/codeware/prod/restart` restarts the production server
- `GET /api/codeware/workspace/remote` returns workspace remote URL
- `GET /api/codeware/worktrees` lists git worktrees
- `POST /api/codeware/worktrees/create` creates a new worktree
- `POST /api/codeware/worktrees/remove` removes a worktree
- Dev sessions use reserved names `sp-webui-dev` and `sp-engine-dev`

## Code Map

- `core/engine/routes_codeware.py` — all `/api/codeware/*` route handlers
- `core/engine/worktree_utils.py` — worktree management utilities
- `core/webui/pages/codeware/index.tsx` — codeware web UI page
- `core/skills/system/codeware/` — codeware agent skill
- `about/version.json5` — version file
- `about/CHANGELOG.md` — changelog

## Search Commands

```bash
rg "api/codeware" core/engine/routes_codeware.py -n
cat core/engine/worktree_utils.py | head -40
find core/skills/system/codeware/ -type f -name "*.md"
cat about/version.json5
```

## Related Features

- `core/features/skill-pilot-development-feature-lifecycle.md`
- `core/features/web-terminal-tmux-sessions.md`
- `core/features/engine-backend-fastapi.md`

## Update Notes

- Dev mode uses tmux sessions named `sp-webui-dev` and `sp-engine-dev`; these are reserved names
- Worktree operations require a clean git state; validate before creating
- `prod/restart` affects the live server; use with caution
