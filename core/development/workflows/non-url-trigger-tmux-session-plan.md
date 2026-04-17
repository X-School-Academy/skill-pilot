# Non-URL TMUX Workflow Trigger Plan

## Summary

Extend tmux-backed workflow execution so an agent skill can trigger `core/bin/run-workflow` from an active tmux-backed agent session without relying on the WebUI URL flow. The implementation injects `TMUX_SESSION_NAME` into Skill Pilot-created tmux shells and tmux-launched agent CLIs, adds tmux-only flags to `core/bin/run-workflow`, and updates the `run-workflow` skill to infer tmux workflow options from user intent and refuse nested workflow triggering when already inside a workflow node.

This preserves current behavior for existing non-tmux workflow CLI usage:

- Keep positional `core/bin/run-workflow <workflow-path> <prompt>`
- Keep existing non-tmux background execution logic unchanged
- Do not support `--promot`
- New flags `--resume` and `--auto-continue` apply only when `--tmux-session=<session-name>` is used

## Key Changes

### 1. Inject tmux session env into shells and agent CLIs

- Update tmux session creation and tmux agent launch paths so `TMUX_SESSION_NAME` is present in:
  - new prompt-driven tmux sessions
  - new shell/bash tmux sessions
  - native-terminal-backed tmux sessions
  - agent CLI subprocesses started inside an existing tmux session

### 2. Add explicit workflow-node runtime marker for loop prevention

- When `_start_workflow_agent_in_session()` launches a workflow node, inject:
  - `SKILL_PILOT_WORKFLOW_NODE=1`
  - `SKILL_PILOT_WORKFLOW_FILE=<repo-relative workflow path>`
  - `SKILL_PILOT_WORKFLOW_NODE_ID=<node-id>`
  - `SKILL_PILOT_WORKFLOW_RUN_ID=<run-id>`

### 3. Extend `core/bin/run-workflow` CLI for tmux mode

- Keep positional mode:
  - `core/bin/run-workflow <workflow-path> <prompt>`
- Add named tmux mode:
  - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt> --tmux-session=<session-name>`
  - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt> --tmux-session=<session-name> --resume`
  - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt> --tmux-session=<session-name> --auto-continue`
- Reject `--resume` and `--auto-continue` unless a real tmux session name is provided.

### 4. Reuse existing workflow-node instruction builder

- Use `build_node_prompt(..., start_by_prompt_mode=not auto_continue)` from `core/engine/mcp_servers/mcp_to_skills/workflow_execution.py`
- Reuse the current terminal workflow wording for the first-node instruction.

### 5. Add tmux-mode workflow monitor path in CLI/runtime

- For tmux mode, `core/bin/run-workflow` starts the workflow monitor in the engine, emits the first-node instruction, and exits.
- The monitor tracks node completion, advances downstream nodes, honors `resume`, and respects prompt-driven versus automatic continuation.

### 6. Update `run-workflow` skill behavior

- Detect recursion first:
  - if `SKILL_PILOT_WORKFLOW_NODE=1`, refuse to trigger
- Detect tmux context:
  - if `TMUX_SESSION_NAME` exists and the user is not asking for background mode, use tmux-mode CLI
  - otherwise use non-tmux CLI
- Infer flags from user intent:
  - `resume`, `continue previous run`, `recover` -> `--resume`
  - `run automatically`, `continue automatically`, `no human pause` -> `--auto-continue`

## Tests

- Positional non-tmux invocation still works unchanged
- Named tmux invocation works with `--workflow`, `--prompt`, `--tmux-session`
- `--promot` is rejected
- `--resume` without `--tmux-session` fails validation
- `--auto-continue` without `--tmux-session` fails validation
- New tmux shell sessions expose `TMUX_SESSION_NAME`
- Tmux-launched agent CLIs receive `TMUX_SESSION_NAME`
- Workflow-node-launched agents receive both `TMUX_SESSION_NAME` and `SKILL_PILOT_WORKFLOW_NODE=1`
- Tmux-triggered skill execution prints the same first-node instruction structure as URL-triggered tmux workflows
- Tmux CLI mode starts the workflow monitor and exits after emitting the first-node instruction
- Resume mode skips completed node outputs
- Prompt-driven mode pauses between nodes and accepts continue signals
- Auto-continue mode advances nodes automatically
- `run-workflow` skill refuses nested workflow triggering
