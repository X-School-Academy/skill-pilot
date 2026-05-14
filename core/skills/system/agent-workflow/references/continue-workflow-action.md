# Continue Workflow Action

Use this reference when the user asks to continue the next node, next agent, or current workflow execution while a terminal workflow run is waiting for a continue signal.

## Steps

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
- If result has `"accepted": false`, report the blocker, such as no active run, wrong trigger mode, or output not ready.

## Notes

- This case only sends a continue signal; it does not start a new workflow run.
- If the current node output file is not ready, verify that the current task has finished before sending the continue signal.
- If the workflow is paused because confirmation was declined or the dialog was closed, keep the conversation in human-in-the-loop mode until the user explicitly asks to continue.
