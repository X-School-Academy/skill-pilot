# Execute Workflow Action

Use this reference when the user asks to run, execute, resume, recover, or validate execution of a saved workflow.

## Steps

### Step 1: Resolve the Workflow Target

1. Accept either:
   - a bare workflow name such as `customer-support-flow`
   - a relative path under `core/workflows/`
   - any relative path under the project root
   - an absolute path that still resolves under the project root
2. If the user gives a bare name, resolve it under `core/workflows/` and append `.json`.
3. Normalize the target to a project-root-relative path when possible.
4. Confirm the resolved file exists before attempting execution.

Important: do not open, read, parse, or analyze the workflow JSON file directly. This case should only resolve the workflow path and verify that the file exists.

### Step 2: Prevent Workflow Recursion

1. Check environment:
   - `SKILL_PILOT_WORKFLOW_NODE`
   - `TMUX_SESSION_NAME`
2. If `SKILL_PILOT_WORKFLOW_NODE=1`, stop immediately.
3. Report that nested workflow triggering is blocked because the current agent is already running inside a multi-step workflow.

### Step 3: Validate the Runtime Entry Point

1. Check whether `core/bin/run-workflow` exists and is executable.
2. If it is missing, stop and report that workflow runtime is not implemented yet.
3. Do not include internal implementation details. This case is only for using the CLI correctly.

### Step 4: Infer Runtime Mode and Flags

1. If `TMUX_SESSION_NAME` is set and the user is not asking to run in background, use tmux mode.
2. Infer tmux-only flags from the user request:
   - pass `--resume` for requests such as `resume`, `continue previous run`, or `recover`
   - pass `--auto-continue` for requests such as `run automatically`, `continue automatically`, or `no human pause`
3. If the user asks to run in background, do not use tmux mode even if `TMUX_SESSION_NAME` is set.
4. Do not invent flags not supported by the CLI.

### Step 5: Build the Execution Command

1. In tmux mode, use:
   - `core/bin/run-workflow --workflow=<workflow-path> --prompt=<prompt>`
   - The CLI auto-detects `TMUX_SESSION_NAME`; pass `--tmux-session=<session-name>` only when overriding the current session.
2. Add tmux-only flags only when they apply:
   - `--resume`
   - `--auto-continue`
3. In non-tmux mode, use:
   - `core/bin/run-workflow <workflow-path> <prompt>`
4. Pass the resolved workflow path only as the CLI workflow argument.
5. Build a structured workflow prompt, not a generic sentence such as `run the workflow`.
6. The prompt should include all user-provided context that the workflow needs, especially:
   - the instruction file path when one is relevant
   - the workspace path when one is relevant
   - any requirement that intermediate files must stay inside the workflow workspace
7. Do not include the workflow file path in the prompt. The workflow runner already receives the path through `--workflow`, and node agents should only receive current-node context.
8. Prefer this shape when task context is available:

```text
Follow the instructions defined at <instruction-file-path>.

Workspace path: <workspace-path>

If you create any intermediate files, save them inside the task workspace above.
```

9. If the user supplied additional workflow-specific context, append it after the base structure instead of replacing the structure.
10. Do not rewrite the user's intent beyond minimal cleanup needed for shell-safe execution.

### Step 6: Execute and Capture Output

1. Run the workflow CLI from the repository root.
2. Capture stdout, stderr, and the exit code.
3. If tmux mode is used, follow the returned first-node instruction exactly.
4. In start-by-prompt runs, each node should finish only the current node, ask the user to approve the node output, and then rely on `continue-workflow-action` from the main process/agent after approval.
5. If the command fails, report whether the failure is:
   - path resolution
   - validation/runtime error
   - missing runner
   - system execution failure

### Step 7: Report the Result

Return:

- resolved workflow path
- prompt used
- tmux session used when applicable
- inferred flags used
- command executed
- exit code
- concise output summary

If the workflow produces structured success output, summarize it briefly. If blocked because the runner is not implemented or because the current agent is already inside a workflow node, say that clearly.

## Key Principles

- Accept workflow files under `core/workflows/` or any valid path under the project root.
- Fail fast on missing files or missing runtime entry point.
- Keep the run to one workflow per invocation.
- Use tmux mode only when the current session exposes `TMUX_SESSION_NAME` and the user is not asking for background execution.
- Never trigger `run-workflow` from inside another workflow node.
- Report exact blockers instead of guessing.
- Focus on how to use the CLI, not on internal runtime design.
