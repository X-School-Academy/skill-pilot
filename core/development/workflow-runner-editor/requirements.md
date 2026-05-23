# Workflow Runner and Editor Requirements

## Goal

Provide a workflow authoring and execution system for Skill Pilot that lets users create multi-step agent workflows, select subagents for each runnable node, run workflows through terminal or background execution, and continue human-in-the-loop workflow runs safely.

## Users / Consumers

- End users creating and running workflows in the Web UI.
- AI agents using the `agent-workflow` skill.
- Developers maintaining workflow JSON, workflow prompts, workflow routes, and workflow tests.
- Background services invoking workflow execution through the engine socket bridge.
- Terminal/tmux sessions running agent workflows.

## Functional Requirements

- The system must store workflow definitions as JSON files under `core/workflows/`.
- A workflow must contain exactly one Start node, one End node, and one or more runnable Agent nodes when useful.
- Runnable workflow nodes must use JSON `type: "agent"`.
- Agent node data must support:
  - `title`
  - `provider_id`
  - `subagent`
  - `responsibility`
- Agent nodes must require a non-empty `title` and `provider_id`.
- Agent nodes must require at least one non-empty value between `subagent` and `responsibility`.
- The current schema must use `data.subagent`; it must not require compatibility behavior for removed `data.skill` workflows.
- The Web UI must let users create, edit, save, delete, and validate workflows.
- The Web UI must let users select subagents using autocomplete sourced from `core/subagents/*/*.md`.
- Workflow file browsing must support listing, loading latest workflow, and loading workflow content.
- Workflow validation must reject malformed node ids, missing required node fields, duplicate nodes, invalid edges, duplicate normalized node names, cycles, and invalid Start/End structure.
- Workflow execution must run agent nodes in dependency order.
- Downstream nodes must wait for required upstream agent outputs.
- Failed or blocked upstream nodes must block dependent downstream nodes.
- Node agents must write their final node result to the output file path assigned in the node prompt.
- Final workflow output must come from agent nodes connected to the End node.

## Execution Modes

- The system must support managed tmux execution from the Web UI through `/api/workflows/execute`.
- Managed tmux execution must use the reserved session name `sp-workflow-execute`.
- The system must support running a workflow in an existing tmux session through `core/bin/run-workflow`.
- When `TMUX_SESSION_NAME` is present and `--tmux-session` is omitted, the CLI must treat the current tmux session as the target workflow monitor session.
- `--tmux-session=<name>` must override auto-detected tmux session selection.
- `--tmux-session=none` must force non-tmux background execution even when `TMUX_SESSION_NAME` is present.
- `--resume` and `--auto-continue` must only apply to tmux-backed workflow monitor mode.
- Non-tmux background execution must run through `skill_agent_infer` and return a JSON summary to stdout.
- Non-tmux background execution must require a background provider capable of writing local node output files.

## Human-in-the-Loop Requirements

- Workflow tmux execution must support `auto_continue`.
- In `auto_continue`, the monitor must detect each node output file, exit the current agent session, and launch the next node agent.
- Workflow tmux execution must support `start_by_prompt`.
- In `start_by_prompt`, the monitor must pause after a node output is written when downstream nodes remain.
- In `start_by_prompt`, the current node agent must ask the user to approve the current node result.
- After approval, the main process/agent must continue the workflow by invoking the `agent-workflow` continue action or `core/bin/run-workflow --continue-terminal-session`.
- Continue requests must fail clearly if:
  - there is no active workflow thread
  - the workflow is not in `start_by_prompt`
  - the workflow is not waiting for continue
  - the current node output file is not ready
  - no downstream nodes remain

## Prompt and Context Requirements

- Node prompts must include:
  - workflow name
  - current node id
  - current node name
  - workflow-level prompt
  - selected subagent
  - node responsibility
  - workflow output root
  - upstream output locations when upstream nodes exist
  - exact output file path to write
- Node prompts must instruct agents not to inspect workflow JSON or run other workflow nodes.
- Node prompts must not include `Workflow file: core/workflows/...`.
- The workflow file path may be used as a CLI argument, route input, state field, log field, or retrieval metadata, but not as current-node prompt content.

## Interfaces

- Web UI:
  - `/workflows`
- Engine APIs:
  - `GET /api/workflows/tree`
  - `GET /api/workflows/latest`
  - `GET /api/workflows/content`
  - `POST /api/workflows/validate`
  - `POST /api/workflows/save`
  - `POST /api/workflows/delete`
  - `POST /api/workflows/execute`
  - `GET /api/workflows/execute/status`
  - `POST /api/workflows/execute/continue`
- CLI:
  - `core/bin/run-workflow <workflow-path> <prompt>`
  - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt>`
  - `core/bin/run-workflow --tmux-session=<name> --workflow=<workflow-path> --prompt=<prompt>`
  - `core/bin/run-workflow --tmux-session=none <workflow-path> <prompt>`
  - `core/bin/run-workflow --continue-terminal-session`
- Agent skill:
  - `core/skills/system/agent-workflow`

## Configuration

- Workflows must live under `core/workflows/`.
- User subagents may live under `core/subagents/user/`.
- System and other subagents may live under other `core/subagents/*/` category folders.
- Workflow output files must be created under `.skillpilot/temp/`.
- Background workflow output defaults to `.skillpilot/temp/background-workflow/`.
- Terminal workflow output defaults to the terminal workflow temp area managed by the engine.

## Safety and Constraints

- Workflow path resolution must prevent traversal outside `core/workflows/`.
- Workflow file names must be normalized and validated.
- Save operations must validate the workflow document before writing.
- New workflow saves must avoid accidental overwrite by using collision-safe file creation.
- Node output paths must be generated from normalized node names.
- Workflow node names must be unique after normalization to prevent output file collisions.
- Tmux session names must be validated before use.
- Starting a new workflow execution must stop any existing workflow execution thread.
- Managed workflow sessions may be killed by the engine when replacing or cleaning up a run.
- Existing tmux session workflow runs must not be treated as engine-owned sessions.
- The workflow runner must not silently continue when a required node output file is missing.

## Compatibility

- Existing workflow files under `core/workflows/` must continue to load if they follow the current `type: "agent"` and `data.subagent` or `data.responsibility` schema.
- Existing Web UI workflow editing flows must continue to support creating new workflows and editing saved workflows.
- Existing tmux terminal sessions must continue to work with `TMUX_SESSION_NAME`.
- The `agent-workflow` skill must remain the supported agent-facing way to create, run, and continue workflows.
- The frozen feature index must remain available at `core/features/workflow-runner-editor.md`.

## Acceptance Criteria

- A user can create a workflow in the Web UI with an agent node using a subagent selected by autocomplete.
- Saving a workflow writes valid JSON under `core/workflows/`.
- Invalid workflow documents return validation errors with rule names and affected node or edge ids.
- `core/bin/run-workflow --tmux-session=none core/workflows/user-subagent-test-workflow.json "Run the user subagent test workflow."` runs in background mode and completes all four sample nodes when the background provider is configured.
- A start-by-prompt tmux workflow pauses after a node output is written and resumes only after a continue signal.
- An auto-continue tmux workflow launches downstream nodes without manual approval after output files appear.
- Node prompts do not contain `Workflow file:`.
- Regression tests pass:

```bash
uv --directory core/engine run pytest tests/test_run_workflow_cli.py tests/test_subagent_install.py
```

