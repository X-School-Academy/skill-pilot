---
name: continue-workflow-execution
description: Use when the user asks to continue the next node or continue the next agent, or continue the workflow, or simply say next or continue in an AI agent node execution belong to a multi-step workflow.
---

# AI Builder - Continue Workflow Execution

Continue a running terminal workflow execution when it is waiting for a user continue signal.

## When to Use This Skill

- The user asks to continue a workflow node in terminal execution mode
- The current AI agent node task has been completed, and the output file has been created
- The user says phrases such as "continue next node", "continue next agent", or "continue workflow", or simply say "next" or "continue" in an AI agent node execution belong to a multi-step workflow

## Your Roles in This Skill

- **Project Manager**: Confirm there is an active terminal workflow run and that continue mode is applicable.
- **Backend Developer**: Send the continue signal through the CLI bridge safely after confirmation.
- **Technical Writer**: Report whether continue was accepted, deferred, or blocked, and why.

## Instructions

### Step 1: Ask for Confirmation

Run:

```bash
core/bin/ask-user-confirm "Please confirm whether you want to continue to the next agent node."
```

### Step 2: Branch on the Confirmation Result

- If the command exits with code `0`, continue immediately to Step 3.
- If the command exits with code `1`, treat the workflow as paused for human-in-the-loop review. Tell the user that execution is waiting for their instruction, and do not run the workflow continue command yet.
- While paused, wait until the user explicitly says `continue` or clearly instructs you to resume the next agent node.

### Step 3: Trigger the Continue Signal

Run:

```bash
core/bin/run-workflow --continue-terminal-session
```

### Step 4: Interpret the Result

- If result has `"accepted": true`, report that the workflow will continue.
- If result has `"accepted": false`, report the blocker (for example no active run, wrong trigger mode, or output not ready).

## Notes

- This skill only sends a continue signal; it does not start a new workflow run.
- If the current node output file is not ready, verify that the current task has finished before sending the continue signal.
- If the workflow is paused because confirmation was declined or the dialog was closed, keep the conversation in human-in-the-loop mode until the user explicitly asks to continue.
