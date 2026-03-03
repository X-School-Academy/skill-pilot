# Terminal Workflow Execute Development Plan (For Approval)

Requirement reference:
- `core/development/workflows/terminal-execute.md`
- `core/development/workflows/run-workflow.md`

## 1. Goal

Deliver a workflow execution path that can run a saved workflow in two modes:

1. Background mode via `core/bin/run-workflow`
2. Interactive terminal mode via a new backend-managed workflow execute thread launched from the WebUI new-session flow

The feature must keep the existing workflow graph validation rules, reuse existing terminal session infrastructure where possible, and standardize prompt assembly so both execution modes use the same node-level prompt contract.

## 2. Current Codebase Review and Gaps

### Existing behavior

1. `core/webui/pages/tasks/index.tsx`
   - The Tasks execute dialog already builds a workflow execution prompt and redirects to `/?new_session=true&prompt=...`.
   - It does not pass a dedicated `workflow` query parameter yet.

2. `core/webui/pages/index.tsx`
   - The home page already reads `new_session=true&prompt=...` and prefills the new-session prompt.
   - `handleStart()` posts to `POST /api/terminal/tmux/create` and creates a normal agent tmux session.
   - There is no workflow-aware start path, no workflow thread creation, and no lifecycle coordination with workflow execution state.

3. `core/engine/routes.py`
   - `POST /api/terminal/tmux/create` creates either a WebUI tmux session or native-terminal tmux session.
   - Session names are generated with general prefixes; there is no fixed `sp-workflow-execute` session flow.
   - There is no backend registry for a workflow execute thread.

4. `core/engine/mcp_servers/mcp_to_skills/run_workflow.py`
   - `run_workflow()` is already implemented.
   - It executes agent nodes in parallel with a worker pool and calls `infer_fn()` directly, which means background execution does not use terminal sessions.
   - Prompt construction currently embeds upstream outputs inline in the prompt, not as file-based handoff paths.

5. `core/engine/mcp_servers/mcp_to_skills/service.py`
   - `new_agent_session` exists and reuses the latest tmux session provider/security metadata.
   - It swaps the active CLI agent inside an existing tmux session, which is the closest current primitive for terminal workflow node-by-node execution.
   - It currently targets the latest recorded agent tmux session and derives the provider from session metadata, so it cannot safely drive `sp-workflow-execute` or per-node providers without extension.

### Gaps against the requirement

1. No URL-level workflow identity is carried from Tasks into New Session.
2. No backend concept of a single active workflow execute thread.
3. No fixed workflow tmux session name or cleanup policy tied to workflow execution.
4. No file-based workflow output handoff under `.skillpilot/temp/background-workflow` or `.skillpilot/temp/terminal-workflow`.
5. `run_workflow()` prompt format does not match the new required prompt contract.
6. No terminal-mode orchestrator or session-targeted agent rotation API that can safely advance node-by-node inside `sp-workflow-execute`.

## 3. Finalized Design Decisions

1. Keep `core/bin/run-workflow` as the CLI entry point.
   - The shell wrapper remains unchanged.
   - The Python runtime behind it will be updated.

2. Introduce a dedicated workflow execution coordinator in the engine.
   - Background mode and terminal mode should share graph traversal logic.
   - Mode-specific differences should live in pluggable execution backends.

3. Use one fixed tmux session name for terminal workflow runs.
   - Session name: `sp-workflow-execute`
   - This session will be reused across nodes during one workflow run.

4. Keep terminal workflow execution single-run and single-threaded at the top level.
   - Only one active workflow execute thread may exist in the backend.
   - Starting a new workflow execute thread must clean up the prior thread and fixed tmux session first.

5. Use file-based node output handoff for both modes.
   - Background mode base root: `.skillpilot/temp/background-workflow/`
   - Terminal mode base root: `.skillpilot/temp/terminal-workflow/`
   - Each run gets a unique `run_id` subdirectory under the selected base root.

6. The workflow node `provider_id` remains authoritative for both execution modes.
   - Background mode uses the node `provider_id` exactly as it does now.
   - Terminal mode must also use the node `provider_id` for each node command.
   - The New Session screen controls only workflow-level permissions (`sandbox`, `auto`, `network`) and terminal presentation (`native_terminal` vs WebUI terminal).
   - In workflow mode, the UI provider selector should be hidden, disabled, or replaced with a note that providers are defined by the workflow nodes.

7. Terminal mode should execute nodes sequentially in the shared tmux session.
   - This is required because the terminal execution flow replaces the active CLI agent inside one shared tmux session.
   - Background mode may keep its current parallel behavior if desired, but prompt/output handling should be aligned.

8. Do not add a new workflow node schema field in this phase.
   - The node-specific instruction block is derived from existing Agent fields: `skill` and optional `responsibility`.

9. The workflow API path contract should be relative to `core/workflows/`.
   - Example API value: `customer-support/triage.json`
   - Human-facing prompt text may still display the project path `core/workflows/customer-support/triage.json`.

## 4. Target Architecture

### Backend components

1. Workflow execution coordinator
   - New Python module under `core/engine/mcp_servers/mcp_to_skills/`
   - Responsibilities:
     - load and validate workflow JSON
     - build DAG state
     - compute executable nodes
     - assemble prompts
     - dispatch node execution through either background inference or terminal session control
     - track node status and output files

2. Workflow execute thread manager
   - New backend state in `core/engine/routes.py` or a small helper module
   - Responsibilities:
     - create one active workflow thread
     - track thread metadata (workflow path, tmux session name, status, started_at)
     - track the active `run_id` and `output_root`
     - stop old thread before starting a new one
     - terminate thread if `sp-workflow-execute` tmux session disappears

3. Workflow-specific tmux helpers
   - New helper(s) in `core/engine/routes.py` or nearby utilities
   - Responsibilities:
     - create a tmux session with the explicit name `sp-workflow-execute`
     - return an attach command for `sp-workflow-execute` using `_build_tmux_attach_command_any()` or an equivalent helper that does not require the `webui-live-` prefix

4. Session-targeted agent rotation helper
   - New internal service/helper in `core/engine/mcp_servers/mcp_to_skills/service.py`
   - Responsibilities:
     - accept an explicit `session_name`
     - accept an explicit node `provider_id`
     - reuse workflow-level `sandbox`, `auto`, and `network` settings
     - exit the active CLI agent in the target tmux session and start the next one
   - This helper must not rely on the current latest-session lookup.

5. Workflow terminal API
   - New API endpoint(s) for starting terminal workflow execution from WebUI
   - This should be separate from the generic `terminal/tmux/create` flow to avoid overloading unrelated behavior.

### Frontend components

1. Tasks page
   - Include the workflow file path in the new-session URL.

2. New Session screen (`/`)
   - Detect workflow mode from query params.
   - Preserve the normal prompt text area, but switch the Start action to a workflow-aware backend call when a workflow is selected.
   - Continue honoring the permission settings from the new-session controls.
   - In workflow mode, do not treat the New Session provider selector as the source of truth for node execution.

## 5. Implementation Phases

### Phase 1: WebUI input and routing changes

1. Update `core/webui/pages/tasks/index.tsx`
   - When execute mode is `workflow`, include:
     - `new_session=true`
     - `prompt=<workflow instruction prompt>`
     - `workflow=<workflow json path relative to core/workflows>`
   - Keep the current generated prompt text, but append:
     - the task workspace path
     - explicit instruction that intermediate files must be saved in the task workspace
   - In the human-facing prompt text, display the workflow path as `core/workflows/{workflow_relative_path}` for clarity.

2. Update `core/webui/pages/index.tsx`
   - Read the `workflow` query param.
   - Store workflow mode state in the new-session form.
   - Show workflow context in the UI so the user can confirm what will run.
   - In workflow mode, hide or disable the provider selector and show that providers come from the workflow nodes.
   - Branch `handleStart()`:
     - if no workflow: keep current `POST /api/terminal/tmux/create`
     - if workflow is set: call a new workflow execute endpoint and send only workflow-level permission and terminal settings

### Phase 2: Backend workflow execute API and lifecycle

1. Add a new endpoint in `core/engine/routes.py`
   - Recommended path: `POST /api/workflows/execute`

2. Request payload
   - `workflow`: workflow path relative to `core/workflows/`
   - `prompt`: workflow system prompt from the new-session screen
   - `sandbox`: selected sandbox mode
   - `auto`: selected auto-approve flag
   - `network`: selected network flag
   - `native_terminal`: whether to open in native terminal

3. Endpoint behavior
   - validate that `workflow` is relative to `core/workflows/`
   - terminate any existing workflow execute thread
   - kill any existing `sp-workflow-execute` tmux session
   - create a fresh `sp-workflow-execute` tmux session as a plain shell session, not a pre-bound provider session
   - store workflow-level execution settings (`sandbox`, `auto`, `network`, `native_terminal`) in workflow execute state
   - start one backend workflow execution thread bound to that session
   - optionally open the native terminal attached to `sp-workflow-execute`
   - return:
     - session name
     - attach command built with `_build_tmux_attach_command_any()` or an equivalent any-session helper
     - workflow thread status
     - native terminal open status

4. Lifecycle watcher
   - Reuse or extend existing periodic housekeeping in `routes.py`
   - If the active workflow thread exists but `sp-workflow-execute` no longer exists, mark the thread terminated and clean up in-memory state

5. Engine reload cleanup
   - Ensure engine reload path also kills `sp-workflow-execute` if present
   - Ensure any active workflow execute thread state is cleared during reload startup

### Phase 3: Shared workflow execution coordinator

1. Refactor `core/engine/mcp_servers/mcp_to_skills/run_workflow.py`
   - Split current monolithic `run_workflow()` logic into:
     - workflow loading and validation
     - graph dependency preparation
     - prompt assembly
     - execution backend interface

2. Add execution backends
   - `BackgroundWorkflowExecutor`
     - uses `infer_fn(prompt, provider_id)` as today
     - writes node outputs to mode-specific files
   - `TerminalWorkflowExecutor`
     - uses tmux plus a session-targeted agent rotation helper
     - runs one node at a time in `sp-workflow-execute`
     - builds each node command using the node `provider_id`
     - reuses workflow-level `sandbox`, `auto`, and `network` settings for every node command
     - waits for each node output file to appear before advancing

3. Keep deterministic node ordering
   - When multiple nodes are ready:
     - background mode may keep parallel workers
     - terminal mode must process in stable order (recommended: ascending node id)

### Phase 4: Prompt contract unification

1. Replace the current inline-output prompt in `run_workflow.py`
2. Introduce one prompt builder shared by both execution modes
3. Use mode-specific output directories in generated prompt text

### Phase 5: File output and handoff implementation

1. Add run directory preparation
   - Generate a unique `run_id` for each workflow run
   - Background mode creates `.skillpilot/temp/background-workflow/{run_id}/` and must not clear the entire background base root
   - Terminal mode creates `.skillpilot/temp/terminal-workflow/{run_id}/`; because terminal mode is singleton, it may prune prior terminal-run artifacts before starting

2. Node output convention
   - Each agent node writes:
     - `{output_root}/{node_uid}.md`

3. Terminal completion detection
   - The orchestrator waits until:
     - the output file exists
     - and tmux output indicates the command completed successfully enough to proceed
   - The file existence check is the primary gate

4. Final run summary
   - Background mode returns structured JSON result as today
   - Terminal mode should persist a lightweight run summary in memory for API response/future status endpoints

### Phase 6: Verification

1. Backend tests
   - workflow path validation
   - active thread singleton enforcement
   - session-targeted agent rotation using an explicit `session_name`
   - node-level provider selection in terminal mode
   - tmux session replacement
   - prompt generation snapshots
   - run-scoped output directory isolation

2. Manual integration checks
   - Task page -> New Session -> Web terminal workflow run
   - Task page -> New Session -> Native terminal workflow run
   - repeated Start clicks replace the old run cleanly
   - killing `sp-workflow-execute` stops the backend thread
   - engine reload clears the workflow session/state

## 6. Detailed Runtime Flow

### A. Tasks page to New Session

1. User opens a task in `core/webui/pages/tasks/index.tsx`
2. User chooses `Execute -> Workflow`
3. Frontend builds:
   - workflow path: `<name>.json` relative to `core/workflows/`
   - prompt text referencing the instruction file and optional reference files
   - task workspace path note
4. Frontend redirects to:
   - `/?new_session=true&prompt=<...>&workflow=<...>`

### B. New Session to backend execute

1. `core/webui/pages/index.tsx` reads `prompt` and `workflow`
2. User adjusts:
   - sandbox
   - auto
   - network
   - web terminal vs native terminal
   - provider source is shown as the workflow node definitions, not the New Session provider selector
3. User clicks Start
4. Frontend calls `POST /api/workflows/execute`

### C. Backend session bootstrap

1. Validate request payload
2. Resolve the workflow file path relative to `core/workflows/`
3. Stop old workflow execute thread if active
4. Kill tmux session `sp-workflow-execute` if it exists
5. Create fresh `sp-workflow-execute` as a plain bash tmux session
6. Store workflow-level execution settings and generate a `run_id`
7. Start backend workflow thread
8. If native mode:
   - open OS terminal attached to `sp-workflow-execute`
9. Return session details to frontend, including an attach command that supports the fixed session name

### D. Terminal workflow thread execution

1. Create `run_id` and `output_root = .skillpilot/temp/terminal-workflow/{run_id}/`
2. Load and validate workflow JSON
3. Build executable node order from the DAG
4. For each ready Agent node:
   - build prompt
   - dispatch via a session-targeted internal helper
     or an explicitly extended `new_agent_session` contract that accepts `session_name` and node `provider_id`
   - wait for `{output_root}/{node_uid}.md`
   - mark node complete
   - unlock downstream nodes whose dependencies are now satisfied
5. After all nodes complete:
   - mark workflow thread finished
   - leave `sp-workflow-execute` running for user review

### E. Background CLI workflow execution

1. User runs `core/bin/run-workflow <workflow> <prompt>`
2. CLI resolves the workflow file and enters Python runtime
3. Runtime creates `run_id` and `output_root = .skillpilot/temp/background-workflow/{run_id}/`
4. Runtime executes nodes via `infer_fn()`
5. Each completed node writes `{output_root}/{node_uid}.md`
6. Runtime returns the JSON summary result

## 7. Prompt Specifications

### A. New Session system prompt seed (from WebUI)

This is the prompt the user edits in the new-session screen. For workflow launches it becomes the workflow-level system prompt and should include:

```text
Execute workflow core/workflows/{workflow_relative_path} in terminal.

Follow the instructions defined at {instruction_file_path}.

Workspace path: {task_workspace_path}

If you create any intermediate files, save them inside the task workspace above.

Reference files:
- {reference_file_1}
- {reference_file_2}
```

Rules:
- `Reference files:` section is included only when files were selected.
- `task_workspace_path` is the folder that contains the instruction file.

### B. Shared agent node prompt template

This prompt should replace the current `run_workflow.py` prompt format:

```text
You are running as an AI agent node inside a multi-step workflow.

Workflow name: {workflow_name}
Workflow file: core/workflows/{workflow_relative_path}
Current AI agent node UID: {node_uid}
Current AI agent node name: {node_title}
Current AI agent provider: {node_provider_id}

Workflow system prompt:
{workflow_prompt}

Node-specific instruction (derived from workflow node data):
- Skill: {node_skill}
- Responsibility: {node_responsibility}

Task workspace:
{task_workspace_path}

Workflow output root:
{output_root}

If you have upstream inputs (and this node is not the START node), the upstream outputs are stored in:
{upstream_file_1}
{upstream_file_2}
...

Read those files to get all required context before you start.

When you finish:
1. Write your final output to {output_root}/{node_uid}.md
2. Keep the output concise and structured so downstream nodes can consume it
3. If you make assumptions, state them before the final result
4. Do not write output files outside the task workspace or workflow output root unless explicitly required
```

Rules:
- Omit the `Skill:` line when skill is empty.
- Omit the `Responsibility:` line when responsibility is empty.
- Omit the upstream file list for nodes whose only upstream node is `START`.
- Do not add a new `node_prompt` field in this phase; the node-specific instruction is derived from the existing node `skill` and optional `responsibility`.

### C. Background mode execution prompt

Background mode uses the same prompt body as terminal mode, but with:

```text
Workflow output root:
.skillpilot/temp/background-workflow/{run_id}
```

### D. Terminal mode execution prompt

Terminal mode uses the same prompt body as background mode, but with:

```text
Workflow output root:
.skillpilot/temp/terminal-workflow/{run_id}
```

## 8. Concrete File Change Plan

### WebUI

1. `core/webui/pages/tasks/index.tsx`
   - Add `workflow` query param to the redirect URL
   - Enrich workflow launch prompt with workspace/intermediate-file guidance

2. `core/webui/pages/index.tsx`
   - Parse/store workflow query state
   - Add workflow-aware Start flow
   - Hide or disable the provider selector in workflow mode
   - Preserve existing non-workflow new-session behavior

### Engine backend

1. `core/engine/routes.py`
   - Add `POST /api/workflows/execute`
   - Add workflow thread singleton state
   - Add explicit-name tmux session helpers for `sp-workflow-execute`
   - Use any-session attach command handling for `sp-workflow-execute`
   - Add `sp-workflow-execute` session cleanup and watcher logic
   - Add engine reload cleanup hook

2. `core/engine/mcp_servers/mcp_to_skills/run_workflow.py`
   - Refactor for shared coordinator model
   - Update prompt builder
   - Generate a `run_id` and run-scoped `output_root`
   - Add file output writing
   - Keep structured result contract

3. `core/engine/mcp_servers/mcp_to_skills/service.py`
   - Add a session-targeted agent rotation helper for terminal mode orchestration
   - Do not reuse the current latest-session lookup in workflow mode
   - Build each terminal node command from the node `provider_id` plus workflow-level permission settings

4. `core/engine/mcp_servers/mcp_to_skills/cli.py`
   - Keep `run-workflow` contract stable
   - Only extend `new_agent_session` if you want CLI parity for explicit `session_name` and `provider_id`

### New module(s)

1. Recommended new helper:
   - `core/engine/mcp_servers/mcp_to_skills/workflow_execution.py`
   - Purpose:
     - shared DAG traversal
     - prompt assembly
     - run-scoped output root generation
     - executor abstraction

2. Optional new helper:
   - `core/engine/workflow_execute_state.py`
   - Purpose:
     - singleton thread/session lifecycle state
     - workflow-level security settings and active `run_id`

## 9. Risks and Mitigations

1. Risk: the current `new_agent_session` contract can target the wrong tmux session
   - Mitigation: add explicit `session_name` targeting for workflow node rotation

2. Risk: provider authority is ambiguous between workflow node config and New Session UI
   - Mitigation: keep node `provider_id` authoritative and use the New Session controls only for permissions and terminal presentation

3. Risk: background runs can overwrite or delete each other's output files
   - Mitigation: use a unique `run_id` directory per background run

4. Risk: a node may create the output file before the CLI fully exits
   - Mitigation: file existence is the required unblock signal; tmux output is only secondary confirmation

5. Risk: engine reload or manual tmux kill leaves stale in-memory state
   - Mitigation: add explicit cleanup in both reload path and watcher loop

6. Risk: path contracts may drift between API input and human-facing prompt text
   - Mitigation: keep API workflow paths relative to `core/workflows/` and render project paths separately in prompt text only

## 10. Open Implementation Choices

1. Preferred choice: call internal Python helpers for terminal orchestration instead of shelling out to `core/bin/tool-cli new_agent_session` from the backend thread
   - Reason: simpler error handling, no extra process hop, explicit session targeting, and easier test coverage

2. Optional follow-up choice: extend `core/bin/tool-cli new_agent_session` and `cli.py` to accept explicit `session_name` and `provider_id`
   - Do not use the current `new_agent_session` contract for workflow execution as-is

3. Preferred choice: add a lightweight `GET /api/workflows/execute/status` endpoint later only if the UI needs live status
   - Not required for the first implementation unless you want progress visible in the WebUI

## 11. Approval Gate

Approve this plan before implementation. Once approved, the implementation should follow this document, and any deviation should be recorded back into this file before code changes proceed.
