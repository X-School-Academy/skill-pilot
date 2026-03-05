# Continue Workflow Development Plan (Implemented)

Requirement reference:
- `core/development/workflows/continue-workflow.md`
- `core/development/workflows/terminal-execute-plan.md`

## 1. Goal

Implement a controllable "continue next node" flow for terminal tmux workflow execution, with two modes:
1. Auto continue
2. Continue only after explicit user prompt

## 2. Original Gaps

1. No workflow-level UI option to choose how the next node is triggered.
2. No dedicated system skill to interpret "continue workflow" user intent and trigger the runtime.
3. `core/bin/run-workflow` does not expose terminal-continue controls.
4. Terminal runtime behavior is not standardized for:
   - output file not ready,
   - current agent exit,
   - final node completion.

## 3. Implementation Status

All planned phases are implemented.

### Phase 1: WebUI option for next-node trigger

Status: Completed

1. Updated workflow execute UI in `core/webui/pages/tasks/index.tsx`:
   - Add dropdown: `Next Node Trigger`.
   - Show only when execute mode is workflow.
   - Default to `Auto continue`.
2. Passed selected trigger mode through new-session URL query via `next_node_trigger`.
3. Updated new-session UI in `core/webui/pages/index.tsx` to:
   - read `next_node_trigger` from query,
   - allow user override before start,
   - send `next_node_trigger` in workflow execute API payload.

### Phase 2: Backend/API contract updates

Status: Completed

1. Extended workflow execute API payload in `core/engine/routes.py`:
   - add `next_node_trigger` with allowed values:
     - `auto_continue`
     - `start_by_prompt`
2. Added validation and persisted this field in workflow runtime state.
3. Added continue endpoint:
   - `POST /api/workflows/execute/continue`
4. Extended workflow status state with pause/continue metadata:
   - `waiting_for_continue`
   - `current_output_file`
   - `current_node_id`
   - `current_provider_id`
   - other execution-trace fields.

### Phase 3: CLI updates for run-workflow

Status: Completed

1. Updated argument parsing in workflow CLI entrypoint (behind `core/bin/run-workflow`):
   - add `--continue-terminal-session` (bool),
   - add `--continue-source` (string label for log traceability).
2. Added CLI continuation flow:
   - sends socket operation `continue_workflow_terminal`.
3. Kept normal workflow execution path intact (non-continue mode still uses workflow + prompt).

### Phase 4: Continue runtime behavior

Status: Completed

1. In terminal workflow executor/orchestrator code:
   - If mode is `auto_continue`, keep existing next-node behavior.
   - If mode is `start_by_prompt`, pause after each non-final node completion until continue signal is received.
2. On continue signal:
   - If current output file is missing:
     - write warning to tmux session and keep current node active.
   - If output file exists:
     - send `exit-session` sequence to terminate current agent process.
   - If no remaining nodes:
     - execute `echo 'The workflow has completed.'`
   - Else:
     - start next node.
3. Added tmux warning message when output is not ready:
   - "User asked to continue to the next workflow node, but the current node output file is not ready. Please finish the current task first."

### Phase 5: System skill for continue action

Status: Completed

1. Added new skill:
   - `core/skills/system/continue-workflow-execution/SKILL.md`
2. Skill responsibilities:
   - detect user continue intent,
   - verify active multi-agent workflow context,
   - verify current output file readiness,
   - call workflow continue path (API/CLI) safely.
3. Add clear fallback response when no active workflow or output is not ready.

### Phase 6: Verification

Status: Partially completed (static/contract checks done, manual runtime scenario still recommended)

1. Completed checks:
   - `python3 -m py_compile core/engine/routes.py core/engine/mcp_servers/mcp_to_skills/cli.py core/engine/mcp_servers/mcp_to_skills/service.py`
   - `pnpm -C core/webui exec tsc --noEmit`
   - `core/bin/run-workflow --help` verifies new flags are exposed.
2. Recommended follow-up manual checks:
   - Auto continue mode full run.
   - Start-by-prompt pause/continue flow.
   - Missing output file warning behavior in tmux.

## 4. Final Changed Files

1. `core/webui/pages/tasks/index.tsx`
2. `core/webui/pages/index.tsx`
3. `core/engine/routes.py`
4. `core/engine/mcp_servers/mcp_to_skills/cli.py`
5. `core/engine/mcp_servers/mcp_to_skills/service.py`
6. `core/skills/system/continue-workflow-execution/SKILL.md`

## 5. Final Decisions

1. Continue signal transport:
   - Implemented as both API and CLI.
2. Trigger mode naming:
   - Finalized as `auto_continue` and `start_by_prompt`.
3. Output readiness contract:
   - Implemented with file existence as the primary readiness gate.
4. Continue source label:
   - `--continue-source` is for traceability/logging only.

## 6. Review Gate

Implementation is complete. Use this file as the final implementation record for review and QA signoff.
