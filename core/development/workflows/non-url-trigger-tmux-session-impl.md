# Non-URL TMUX Workflow Trigger Implementation

## Summary

Implemented non-URL tmux workflow triggering so an active tmux-backed agent session can start a workflow through `core/bin/run-workflow` without relying on the New Session window URL flow.

The implementation now:

- injects `TMUX_SESSION_NAME` into Skill Pilot tmux shells and tmux-launched agent CLIs
- adds tmux-mode workflow startup to `core/bin/run-workflow`
- returns the first workflow-node instruction to the current agent in tmux mode
- runs the workflow monitor in the engine thread while the CLI exits
- prevents nested workflow triggering from inside workflow nodes
- makes `--continue-terminal-session` use the same exit-session and next-node behavior as the URL-triggered workflow path

## Files Updated

### Core workflow runtime

- `core/engine/routes_shared.py`
- `core/engine/routes.py`
- `core/engine/mcp_servers/mcp_to_skills/service.py`
- `core/engine/mcp_servers/mcp_to_skills/cli.py`

### Skill and docs

- `core/skills/system/run-workflow/SKILL.md`
- `core/development/video-coding-project/non-url-trigger-tmux-session-plan.md`

### Tests

- `core/engine/tests/test_run_workflow_cli.py`
- `core/engine/tests/test_file_manager_routes.py`

## What Was Implemented

### 1. TMUX session environment injection

Added tmux session initialization so Skill Pilot-created tmux sessions export:

- `TMUX_SESSION_NAME=<session-name>`

This was applied to:

- named workflow tmux sessions
- normal webui live tmux sessions
- native terminal tmux sessions
- reusable shell tmux sessions

Also updated provider command payload generation so tmux-launched agent CLIs receive `TMUX_SESSION_NAME` in their subprocess environment.

### 2. Workflow-node runtime markers

When a workflow node is launched into tmux by the workflow monitor, the child agent CLI now receives:

- `SKILL_PILOT_WORKFLOW_NODE=1`
- `SKILL_PILOT_WORKFLOW_FILE=<workflow-path>`
- `SKILL_PILOT_WORKFLOW_NODE_ID=<node-id>`
- `SKILL_PILOT_WORKFLOW_RUN_ID=<run-id>`

This allows skills such as `run-workflow` to refuse recursive workflow startup from inside a workflow node.

### 3. `core/bin/run-workflow` tmux mode

Extended the workflow CLI bridge to support:

- positional mode:
  - `core/bin/run-workflow <workflow-path> <prompt>`
- named tmux mode:
  - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt> --tmux-session=<session-name>`
  - optional tmux-only flags:
    - `--resume`
    - `--auto-continue`

Rules implemented:

- no `--promot` support
- `--resume` and `--auto-continue` are rejected unless a real tmux session is provided
- `--tmux-session=none` falls back to the existing non-tmux behavior
- positional behavior remains unchanged for non-tmux execution

### 4. External-session workflow monitor startup

Added engine-side startup support for workflows that run in an already-existing tmux session instead of the dedicated `sp-workflow-execute` session.

The tmux-mode CLI path now:

1. sends a `start_workflow_terminal` request through the engine socket
2. starts the workflow monitor thread inside the engine
3. computes the first runnable node
4. builds that node prompt using the existing shared `build_node_prompt(...)` logic
5. returns the first-node instruction text to stdout
6. exits while the engine monitor thread continues managing the workflow

### 5. First node handled by current agent, downstream nodes by monitor

For the external tmux path, the monitor thread now supports an `external_first_node` mode.

Behavior:

- the first node is not auto-launched into tmux by the monitor
- instead, the current agent receives the exact node instruction and performs the work
- the monitor waits for that node’s expected output file
- after the output file exists, downstream workflow execution continues using the existing monitor thread logic

This preserves the normal workflow runtime behavior while letting the current tmux-backed agent become node 1.

### 6. Continue-path alignment with URL-triggered workflow logic

The original URL-triggered workflow path already:

- waits for node output
- pauses in `start_by_prompt` mode
- uses provider `exit-session` shortcuts from `config/ai_providers.json5`
- then starts the next node

The external tmux path initially had two regressions:

1. it did not always know the active provider for the first node session, so continue could skip the configured exit shortcut
2. the heartbeat watcher still checked only `sp-workflow-execute`, which caused external-session workflows to be reset to `terminated`

Both were fixed:

- the external-first-node path now resolves the active provider from session metadata or tmux process inspection before waiting for continue
- the heartbeat watcher now checks the real tracked workflow session name from workflow state, not a hard-coded session

This makes `core/bin/run-workflow --continue-terminal-session` behave the same way as the URL-triggered workflow path.

### 7. `run-workflow` skill update

Updated `core/skills/system/run-workflow/SKILL.md` so the skill now:

- does not open or analyze workflow JSON directly
- only resolves the workflow path and verifies the file exists
- blocks recursive workflow startup when `SKILL_PILOT_WORKFLOW_NODE=1`
- uses tmux mode only when `TMUX_SESSION_NAME` is set and the user is not asking for background execution
- infers:
  - `--resume` from requests like `resume`, `recover`, `continue previous run`
  - `--auto-continue` from requests like `run automatically`, `continue automatically`, `no human pause`
- requires the workflow prompt passed to `core/bin/run-workflow` to include full structured context, not a bare “run the workflow” sentence

Prompt structure documented in the skill:

```text
Execute workflow core/workflows/<workflow-file>.json.

Follow the instructions defined at <instruction-file-path>.

Workspace path: <workspace-path>

If you create any intermediate files, save them inside the task workspace above.
```

## Tests Added

Added focused tests for:

- CLI input resolution for named and positional workflow arguments
- tmux-only flag validation
- tmux startup request payload generation
- legacy non-tmux CLI behavior
- provider payload env injection including `TMUX_SESSION_NAME` and workflow-node env markers
- workflow base-dir helper visibility
- active provider recovery from session metadata
- heartbeat workflow-session validation using the tracked external tmux session name

## Verification Performed

### Compile checks

```bash
python3 -m py_compile core/engine/routes.py core/engine/routes_shared.py core/engine/mcp_servers/mcp_to_skills/cli.py core/engine/mcp_servers/mcp_to_skills/service.py core/engine/tests/test_file_manager_routes.py core/engine/tests/test_run_workflow_cli.py
```

### Focused test run

```bash
uv run pytest tests/test_run_workflow_cli.py tests/test_file_manager_routes.py
```

Final focused test result:

- `14 passed in 0.43s`

## Notes

- Existing non-tmux `core/bin/run-workflow <workflow-path> <prompt>` logic was preserved.
- External-session workflow runs require the engine process to include the updated code; old runs that were already marked `terminated` cannot be resumed automatically.
- The implementation file documents what was actually completed, including the follow-up fixes for continue behavior and heartbeat session tracking.
