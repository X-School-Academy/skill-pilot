# Continue Workflow Execution (Terminal / tmux)

Requirement reference:
- `core/development/workflows/terminal-execute-plan.md`

## Goal

Support manual or automatic continuation of the next workflow node when running a multi-agent workflow in a terminal tmux session.

## Requirements

1. WebUI execute mode update
   - In the Tasks -> Execute Workflow modal, add a dropdown shown only in workflow mode:
     - `Next Node Trigger: Auto continue | Start by prompt`
   - Behavior:
     - `Auto continue`: keep existing behavior (continue automatically when the current node output is ready).
     - `Start by prompt`: do not auto-continue; wait for a user prompt such as "continue next node".

2. New system skill
   - Add a system agent skill for continuing workflow execution.
   - Trigger conditions:
     - workflow has multiple agent nodes,
     - current node task is finished,
     - user asks to continue (for example: "continue next node", "continue next agent", "continue workflow"),
     - current node output file exists.

3. `core/bin/run-workflow` CLI extension
   - Add arguments for terminal continuation control, including:
     - `--continue-terminal-session` (or equivalent final naming),
     - any additional parameters needed to identify the active workflow run/session.

4. Continue signal handling in terminal runtime
   - When the runtime receives the continue signal:
     - If the current node output file is missing, send a message in the current tmux window:
       - "User asked to continue to the next workflow node, but the current node output file is not ready. Please finish the current task first."
     - If the output file exists, send the `exit-session` key sequence to terminate the current AI agent process cleanly.
     - If there are no remaining nodes, run:
       - `echo 'The workflow has completed.'`
     - Otherwise, start the next node.
