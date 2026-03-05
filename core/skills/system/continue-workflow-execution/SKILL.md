---
name: continue-workflow-execution
description: Continue a terminal tmux workflow run that is paused in start-by-prompt mode. Use when the user asks to continue the next workflow node or continue workflow execution.
---

# AI Builder - Continue Workflow Execution

Continue a running terminal workflow execution when it is waiting for a user continue signal.

## When to Use This Skill

- The user asks to continue a workflow node in terminal execution mode
- The active workflow run was started with `Next Node Trigger = Start by prompt`
- The user says phrases such as "continue next node", "continue next agent", or "continue workflow"

## Your Roles in This Skill

- **Project Manager**: Confirm there is an active terminal workflow run and that continue mode is applicable.
- **Backend Developer**: Send the continue signal through the CLI bridge safely.
- **Technical Writer**: Report whether continue was accepted or blocked, and why.

## Instructions

### Step 1: Trigger Continue Signal

Run:

```bash
core/bin/run-workflow --continue-terminal-session
```

### Step 2: Interpret Result

- If result has `"accepted": true`, report that the workflow will continue.
- If result has `"accepted": false`, report the blocker (for example no active run, wrong trigger mode, or output not ready).

## Notes

- This skill only sends a continue signal; it does not start a new workflow run.
- If the current node output file is not ready, runtime will post a warning inside the tmux session and remain paused.
