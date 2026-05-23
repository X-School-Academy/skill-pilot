# Feature Retrieval Index: Workflow Runner and Editor

## Retrieval Keywords

workflow, workflow runner, workflow editor, workflow execution, workflow monitor, run-workflow, agent-workflow, continue-workflow-action, workflow JSON, workflow node, agent node, type agent, data.subagent, subagent autocomplete, workflow subagent, workflow continue, continue-terminal-session, start_by_prompt, auto_continue, workflow validate, workflow status, workflow save, workflow delete, workflow tree, workflow execute, background workflow, non-tmux workflow, tmux workflow, TMUX_SESSION_NAME, --tmux-session=none, user-subagent-test-workflow, workflow-random-number, workflow-random-string, workflow-concat-number-string, workflow-detect-number, workflow_editor_utils, workflow_execution, run_workflow

## Scope

- JSON-based workflow definition, validation, execution, and continuation
- Workflow file tree and content management in the engine
- Web UI workflow editor, subagent autocomplete, and workflow status page
- Terminal workflow monitor modes: `auto_continue` and `start_by_prompt`
- Non-tmux/background workflow execution through `skill_agent_infer`
- Predefined workflow templates under `core/workflows/`
- Excludes: individual skill execution (see skill agent feature)

## Main Behavior

- Workflow runnable nodes remain JSON `type: "agent"` and select Skill Pilot subagents with `data.subagent`; do not use old `data.skill`.
- Web UI workflow creation selects subagents from `core/subagents/*/*.md` and persists `data.subagent`.
- `GET /api/workflows/tree` and `/latest` return workflow file structure
- `GET /api/workflows/content` returns a workflow JSON file
- `POST /api/workflows/execute` starts a managed tmux workflow run in `sp-workflow-execute`
- `GET /api/workflows/execute/status` polls execution state
- `POST /api/workflows/execute/continue` resumes a waiting `start_by_prompt` node
- `POST /api/workflows/validate` validates a workflow JSON
- `POST /api/workflows/save` and `/delete` manage workflow files
- CLI entry point: `core/bin/run-workflow`
- Existing tmux session mode: `core/bin/run-workflow --workflow=<workflow> --prompt=<prompt>` auto-detects `TMUX_SESSION_NAME`; `--tmux-session=<name>` overrides.
- Background non-tmux mode: `core/bin/run-workflow --tmux-session=none <workflow-path> <prompt>` forces direct background execution and avoids the tmux monitor.
- `auto_continue` mode lets the monitor detect each node output file, exit the current agent, and launch the next provider session.
- `start_by_prompt` mode waits after each node output; after user approval the main process/agent invokes `core/bin/run-workflow --continue-terminal-session`, which signals the monitor to continue.
- Node prompts include current workflow name, current node id/name, subagent, responsibility, output root, upstream output locations, and finish instructions. They must not expose the workflow JSON file path or ask the subagent to inspect the workflow JSON.
- Sample test assets: `core/subagents/user/workflow-*.md` and `core/workflows/user-subagent-test-workflow.json`.

## Code Map

- `core/engine/routes.py` — `/api/workflows/*` route handlers
- `core/engine/routes_shared.py` — tmux workflow monitor state, `start_by_prompt`, `auto_continue`, provider rotation, continue signal, `TMUX_SESSION_NAME`
- `core/engine/workflow/` — workflow engine: `VideoStyle.py`, `course_planner.py`, `llm_adapter.py`, `video_creator.py`, `video_utils/`
- `core/engine/workflow_editor_utils.py` — workflow JSON validation/editing utilities; validates `data.subagent`
- `core/engine/mcp_servers/mcp_to_skills/workflow_execution.py` — workflow graph loading, node prompt construction, output path conventions
- `core/engine/mcp_servers/mcp_to_skills/run_workflow.py` — non-tmux/background `run_workflow` implementation
- `core/engine/mcp_servers/mcp_to_skills/cli.py` — `core/bin/run-workflow` argument parsing, `TMUX_SESSION_NAME` fallback, `--tmux-session=none`
- `core/engine/mcp_servers/mcp_to_skills/service.py` — socket operations `start_workflow_terminal`, `continue_workflow_terminal`, `skill_agent_infer`
- `core/engine/tests/test_run_workflow_cli.py` — regression tests for subagent prompts, tmux env detection, start-by-prompt provider rotation
- `core/engine/tests/test_subagent_install.py` — subagent install regression tests
- `core/bin/run-workflow` — CLI runner
- `core/skills/system/agent-workflow/SKILL.md` — workflow skill entry point
- `core/skills/system/agent-workflow/references/create-update-workflow.md` — workflow authoring rules using `data.subagent`
- `core/skills/system/agent-workflow/references/execute-workflow-action.md` — run mode selection; workflow file path is a CLI argument, not node prompt content
- `core/skills/system/agent-workflow/references/continue-workflow-action.md` — approval and continue signal behavior
- `core/skills/system/agent-workflow/references/workflow-validation-rules.md` — schema and validation rules
- `core/subagents/user/workflow-random-number.md`, `workflow-random-string.md`, `workflow-concat-number-string.md`, `workflow-detect-number.md` — user test subagents
- `core/workflows/` — bundled workflow templates and `user-subagent-test-workflow.json`
- `core/webui/pages/workflows/index.tsx` — workflow editor/runner page

## Search Commands

```bash
rg "data\\.subagent|subagent" core/webui/pages/workflows/index.tsx core/engine/workflow_editor_utils.py core/skills/system/agent-workflow -n
rg "start_by_prompt|auto_continue|continue-terminal-session|TMUX_SESSION_NAME" core/engine/routes_shared.py core/engine/mcp_servers/mcp_to_skills/cli.py core/skills/system/agent-workflow -n
rg "Workflow file:|Do not inspect the workflow JSON|Use Skill Pilot subagent" core/engine/mcp_servers/mcp_to_skills/workflow_execution.py core/engine/tests/test_run_workflow_cli.py -n
find core/subagents -path "*/workflow-*.md" -print
find core/workflows -name "*.json" -print
core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."
```

## Related Features

- `core/features/skill-agent-system.md`
- `core/features/web-terminal-tmux-sessions.md`
- `core/features/vibe-coding-project-manager.md`
- `core/features/course-creator.md`

## Update Notes

- Preserve schema invariant: runnable nodes are `type: "agent"` and use `data.subagent`; no compatibility code for removed `data.skill` workflows.
- Preserve prompt invariant: node agents know only current-node context and output paths; do not include `Workflow file: core/workflows/...` or encourage reading workflow JSON.
- In `start_by_prompt`, the node agent should ask the user to approve current node work; after approval, the main process/agent uses `continue-workflow-action` or `core/bin/run-workflow --continue-terminal-session`.
- In `start_by_prompt`, preserve `previous_provider` until the next node launch so provider rotation exits the current agent before pasting the next launch command.
- Background mode from a tmux shell must use `--tmux-session=none`; otherwise `TMUX_SESSION_NAME` auto-detects existing tmux monitor mode.
- Non-tmux/background mode depends on a background provider capable of writing local output files, usually the Skill Pilot background agent with bash tools.
- Validation: `uv --directory core/engine run pytest tests/test_run_workflow_cli.py tests/test_subagent_install.py`.
- Smoke test: `core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."`
