# Workflow Runner and Editor Feature Instructions

This feature is managed with the **codeware** skill.

## How to Work on This Feature

Use the `codeware` skill for lifecycle work:

- New changes: `update feature` -> `refine` -> `initial` -> `plan` -> `implement` -> `test` -> `review` -> `merge`
- Bug fixes: `fix issues` -> `refine` -> `initial` -> `plan` -> `implement` -> `test` -> `review` -> `merge`
- After a successful merge, run the freeze step and update `core/features/workflow-runner-editor.md`.

## Feature Context

- **Requirements**: `requirements.md`
- **Implementation**: `implementation.md`
- **Plan**: `plan.md`
- **Frozen Feature Index**: `core/features/workflow-runner-editor.md`
- **Related Features**:
  - `core/features/agent-cli.md`
  - `core/features/web-terminal-tmux-sessions.md`
  - `core/features/course-creator.md`
  - `core/features/vibe-coding-project-manager.md`

## Primary Source Files

- `core/webui/pages/workflows/index.tsx`
- `core/engine/routes.py`
- `core/engine/routes_shared.py`
- `core/engine/workflow_editor_utils.py`
- `core/engine/mcp_servers/mcp_to_skills/cli.py`
- `core/engine/mcp_servers/mcp_to_skills/run_workflow.py`
- `core/engine/mcp_servers/mcp_to_skills/workflow_execution.py`
- `core/engine/mcp_servers/mcp_to_skills/service.py`
- `core/bin/run-workflow`
- `core/skills/system/agent-workflow/`
- `core/workflows/`
- `core/subagents/`

## Key Facts for AI Agents

- Workflow runnable nodes must remain `type: "agent"`.
- Agent node data uses `data.subagent`, not `data.skill`.
- There is no required compatibility layer for old skill-based workflow node data.
- The Web UI must autocomplete subagent names from `core/subagents/*/*.md`.
- Node prompts must not reveal the workflow JSON file path or ask node agents to inspect workflow JSON.
- In `start_by_prompt`, the node agent asks for user approval, then the main process/agent invokes `continue-workflow-action` or `core/bin/run-workflow --continue-terminal-session`.
- Background mode from a tmux shell must use `--tmux-session=none`, because omitted `--tmux-session` auto-detects `TMUX_SESSION_NAME`.
- Non-tmux background mode requires a background provider capable of writing output files.

## Agent Instructions

- Preserve user work in `core/workflows/`, `core/subagents/`, and generated agent files.
- Keep docs and tests aligned with the actual runtime contract.
- When changing prompts, check that workflow nodes still receive only current-node context, output paths, and upstream output locations.
- When changing `start_by_prompt`, test provider rotation and continue signaling.
- When changing CLI mode selection, test `TMUX_SESSION_NAME`, explicit `--tmux-session`, and `--tmux-session=none`.
- Do not read or process ignored sensitive files such as `config/.env`.

## Verification

Run targeted checks after workflow changes:

```bash
uv --directory core/engine run pytest tests/test_run_workflow_cli.py tests/test_subagent_install.py
```

Use this smoke test when the background provider is configured:

```bash
core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."
```

