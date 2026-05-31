# Workflow Runner and Editor Implementation

This document summarizes the current implementation after reverse engineering the source. It intentionally focuses on how the code is organized and where future maintainers should look.

## Feature Boundary

The feature spans workflow JSON editing, validation, execution, and continuation. It includes:

- Web UI workflow editor under `core/webui/pages/workflows/index.tsx`
- Engine workflow APIs in `core/engine/routes.py`
- Shared terminal workflow monitor logic in `core/engine/routes_shared.py`
- Workflow schema utilities in `core/engine/workflow_editor_utils.py`
- Background workflow runner under `core/engine/mcp_servers/mcp_to_skills/`
- `agent-workflow` system skill documentation and actions
- Test subagents and sample workflow files

## Workflow Schema

`core/engine/workflow_editor_utils.py` owns workflow document validation and file helpers.

Important implementation details:

- `safe_workflow_path()` resolves workflow paths under `core/workflows/`.
- `build_workflow_tree()` returns the workflow file tree.
- `find_latest_workflow()` finds the latest JSON workflow.
- `normalize_workflow_filename()` and `is_valid_workflow_filename()` enforce workflow file names.
- `validate_workflow_doc()` validates node shape, edge shape, Start/End structure, duplicate ids, duplicate normalized names, graph reachability, and cycles.
- Agent nodes use `data.subagent` and `data.responsibility`; no old `data.skill` compatibility is needed.

## Web UI

`core/webui/pages/workflows/index.tsx` owns the workflow editor screen.

The page:

- loads workflow tree and latest workflow from `/api/workflows/*`
- creates default Start, Agent, and End nodes
- fetches subagent names from `/api/config/subagents`
- exposes subagent autocomplete through `workflow-subagents-list`
- edits agent fields: `title`, `provider_id`, `subagent`, and `responsibility`
- validates workflow documents before save
- saves and deletes workflow files

The UI text uses "Subagent" for workflow agent persona selection. JSON node type remains `"agent"`.

## Engine Routes

`core/engine/routes.py` exposes the workflow API surface:

- `GET /api/workflows/tree`
- `GET /api/workflows/latest`
- `GET /api/workflows/content`
- `POST /api/workflows/validate`
- `POST /api/workflows/save`
- `POST /api/workflows/delete`
- `POST /api/workflows/execute`
- `GET /api/workflows/execute/status`
- `POST /api/workflows/execute/continue`

`POST /api/workflows/execute` creates or replaces the managed tmux session `sp-workflow-execute`, validates request fields, resolves the workflow path, and starts the workflow monitor thread.

`start_workflow_execute_in_session()` is the engine entry point for an existing tmux session. It is called through the socket bridge when `core/bin/run-workflow` starts a terminal-backed workflow.

## Tmux Workflow Monitor

`core/engine/routes_shared.py` owns workflow monitor state and tmux execution.

The global workflow state tracks:

- active thread
- run token
- status
- session name
- managed/external session ownership
- workflow path
- run id
- output root
- current node id/name/output file
- current provider id/bin
- `next_node_trigger`
- waiting-for-continue state

The monitor loads the workflow graph, computes ready nodes from dependencies, builds the current node prompt, launches or waits for the node agent, waits for the expected output file, and advances downstream nodes.

Two continuation modes are implemented:

- `auto_continue`: after the output file appears, the monitor advances to the next ready node.
- `start_by_prompt`: after the output file appears, the monitor sets `waiting_for_continue=True` and waits for `_WORKFLOW_EXECUTE_CONTINUE`.

`request_workflow_continue_signal()` validates that a workflow is active, in `start_by_prompt`, currently waiting, has remaining nodes, and has a current output file. It then sets the continue event.

Provider rotation is handled before launching the next node agent. In `start_by_prompt`, `previous_provider` must be preserved across the approval wait so the next node launch exits the old provider before pasting the new command.

## Background Workflow Runner

The non-tmux background runner lives in `core/engine/mcp_servers/mcp_to_skills/run_workflow.py`.

It:

- resolves workflow paths under `core/workflows/`
- loads and validates workflow graphs
- creates output directories under `.skillpilot/temp/background-workflow/`
- builds node prompts with `build_node_prompt()`
- calls `infer_fn(prompt, provider_id)` for each node
- requires each node to create its expected output file
- marks downstream nodes blocked when upstream nodes fail
- returns `WorkflowRunResult` with status, node status, final outputs, and errors

Although `max_workers` exists in the implementation, the CLI caps execution to one worker because the engine socket bridge handles one request at a time.

## CLI and Socket Bridge

`core/bin/run-workflow` wraps:

```bash
uv --directory core/engine run python -m mcp_servers.mcp_to_skills.cli run-workflow
```

`core/engine/mcp_servers/mcp_to_skills/cli.py` parses:

- positional workflow path and prompt
- `--workflow`
- `--prompt`
- `--tmux-session`
- `--resume`
- `--auto-continue`
- `--continue-terminal-session`
- provider security flags: `--auto`, `--network`, `--sandbox`

Mode selection:

- `--tmux-session=none` forces non-tmux mode.
- an explicit `--tmux-session=<name>` uses terminal workflow monitor mode.
- omitted `--tmux-session` falls back to `TMUX_SESSION_NAME` when set.
- omitted `--tmux-session` with no `TMUX_SESSION_NAME` uses non-tmux background mode.

`core/engine/mcp_servers/mcp_to_skills/service.py` handles socket operations:

- `skill_agent_infer`
- `start_workflow_terminal`
- `continue_workflow_terminal`

Background node execution uses `skill_agent_infer`, which resolves a background provider and calls `llm_get_text()`.

## Node Prompt Construction

`core/engine/mcp_servers/mcp_to_skills/workflow_execution.py` owns workflow graph loading and prompt construction.

`build_node_prompt()` includes:

- workflow name
- current node id and name
- workflow system prompt
- subagent and responsibility
- task workspace when available
- workflow output root
- upstream output glob when needed
- exact output file path
- instruction not to inspect workflow JSON or run other nodes

The prompt intentionally does not include `Workflow file: core/workflows/...`.

## Agent-Workflow Skill

`core/skills/system/agent-workflow/` defines the agent-facing workflow process.

Important references:

- `create-update-workflow.md`: author workflow JSON using `data.subagent`
- `execute-workflow-action.md`: run saved workflows and choose tmux or background mode
- `continue-workflow-action.md`: signal start-by-prompt continuation after user approval
- `workflow-validation-rules.md`: workflow JSON validation rules
- `sample.json`: reference schema

The execute action treats the workflow file path as a CLI argument and avoids putting it in the prompt that reaches node agents.

## Test Assets

User test subagents:

- `core/subagents/user/workflow-random-number.md`
- `core/subagents/user/workflow-random-string.md`
- `core/subagents/user/workflow-concat-number-string.md`
- `core/subagents/user/workflow-detect-number.md`

Sample workflow:

- `core/workflows/user-subagent-test-workflow.json`

Observed background smoke test result on 2026-05-23:

- command forced non-tmux mode with `--tmux-session=none`
- status `ok`
- all four nodes completed
- output root `.skillpilot/temp/background-workflow/20260523-172007-e0a54ea3`
- generated number `472`
- generated string `K7mQ9xR2pL`
- concatenated value `472K7mQ9xR2pL`
- detected digits `47292`

## Verification Surface

Primary tests:

```bash
uv --directory core/engine run pytest tests/test_run_workflow_cli.py tests/test_subagent_install.py
```

Useful manual checks:

```bash
core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."
rg "Workflow file:" core/engine/mcp_servers/mcp_to_skills/workflow_execution.py core/engine/tests/test_run_workflow_cli.py
rg "data\\.subagent|subagent" core/webui/pages/workflows/index.tsx core/engine/workflow_editor_utils.py core/skills/system/agent-workflow -n
```

## Known Gaps and Risks

- CLI help still says omitting `--tmux-session` means non-tmux mode, but current behavior auto-detects `TMUX_SESSION_NAME`.
- Non-tmux background workflow execution depends on a background provider that can write local files.
- Background workflow output directories are cleaned by default for the base background workflow area.
- Node prompt changes are high risk because they affect all providers and both tmux and non-tmux modes.
- Provider rotation and continue signal timing are high risk in `start_by_prompt`.

