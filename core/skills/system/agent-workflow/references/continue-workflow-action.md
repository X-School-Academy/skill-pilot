# Continue Workflow Action

Use this reference when the user asks to continue the next node, next agent, or current workflow execution while a terminal workflow run is waiting for a continue signal.

In start-by-prompt workflow runs, subagent node prompts ask the user to approve the current node's work and then call this action. The subagent does not have enough control to continue the workflow by itself; the main process/agent must run this action after approval.

## Steps

### Step 1: Decide Whether Confirmation Is Needed

- If the user has explicitly approved the current node's work and clearly asked to continue, skip Step 2 and go directly to Step 4.
- If the user has not explicitly approved continuing to the next node, ask for confirmation in Step 2.

### Step 2: Ask for Confirmation

Run:

```bash
core/bin/ask-user-confirm "Please confirm whether you want to continue to the next agent node."
```

### Step 3: Branch on the Confirmation Result

- If the command exits with code `0`, continue immediately to Step 4.
- If the command exits with code `1`, treat the workflow as paused for human-in-the-loop review. Tell the user that execution is waiting for their instruction, and do not run the workflow continue command yet.
- While paused, wait until the user explicitly says `continue` or clearly instructs you to resume the next agent node.

### Step 4: Trigger the Continue Signal

Run:

```bash
core/bin/run-workflow --continue-terminal-session
```

### Step 5: Interpret the Result

- If result has `"accepted": true`, report that the workflow will continue.
- If result has `"accepted": false`, report the blocker, such as no active run, wrong trigger mode, or output not ready.

## Notes

- This case only sends a continue signal; it does not start a new workflow run.
- If the current node output file is not ready, verify that the current task has finished before sending the continue signal.
- If the workflow is paused because confirmation was declined or the dialog was closed, keep the conversation in human-in-the-loop mode until the user explicitly asks to continue.
- Do not inspect the full workflow JSON to infer future nodes; continuation is controlled by the workflow runtime.
