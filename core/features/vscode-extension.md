# Feature Retrieval Index: VSCode Extension

## Retrieval Keywords

VSCode extension, vscode, VS Code, IDE extension, vscode event, api/vscode/event, extensions/vscode, vscode dist, vscode src, vscode skills, IDE integration

## Scope

- VSCode extension for Skill Pilot integration in the IDE
- VSCode event forwarding to the engine
- Excludes: JetBrains integration, Claude Code CLI (separate tools)

## Main Behavior

- `POST /api/vscode/event` receives events from the VSCode extension
- Extension packaged under `extensions/vscode/`
- Extension source in `extensions/vscode/src/`
- Built output in `extensions/vscode/dist/`

## Code Map

- `core/engine/routes_integrations.py` — `POST /api/vscode/event` handler
- `extensions/vscode/src/` — extension source code
- `extensions/vscode/dist/` — built extension
- `extensions/vscode/.vscode/` — extension development config
- `extensions/vscode/images/` — extension icons/images

## Search Commands

```bash
find extensions/vscode/src/ -type f
rg "vscode/event" core/engine/routes_integrations.py -n
ls extensions/vscode/
```

## Related Features

- `core/features/code-executor.md`
- `core/features/agent-cli.md`

## Update Notes

- Extension must be rebuilt (`pnpm build` in `extensions/vscode/`) after source changes
- `extensions/vscode/node_modules/` is gitignored; run `pnpm install` after clone
