# Feature Retrieval Index: Code Executor

## Retrieval Keywords

code executor, execute code, code execution, code_executor, api/execute_code, code runner, python executor, code_v1, sandbox, run code, interpreter

## Scope

- Server-side code execution endpoint
- VSCode event forwarding
- Excludes: terminal (separate feature), workflow execution (separate feature)

## Main Behavior

- `POST /api/execute_code` executes submitted code server-side and returns output
- `POST /api/vscode/event` forwards events from the VSCode extension to the engine
- Code execution is sandboxed within the engine process environment

## Code Map

- `core/engine/routes_integrations.py` — `POST /api/execute_code`, `POST /api/vscode/event`
- `core/engine/code_executor.py` — code execution logic

## Search Commands

```bash
rg "api/execute_code" core/engine/routes_integrations.py -n
cat core/engine/code_executor.py | head -40
rg "vscode/event" core/engine/routes_integrations.py -n
```

## Related Features

- `core/features/web-terminal-tmux-sessions.md`
- `core/features/llm-ai-chat.md`
- `core/features/vscode-extension.md`

## Update Notes

- Code execution runs in the engine process; resource limits should be enforced
- Timeout and output size limits must be maintained to prevent abuse
