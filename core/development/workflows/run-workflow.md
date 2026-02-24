# Run Workflow Design (Execution Spec)

This document defines the runtime design for executing a saved workflow JSON.

## 1. Goal

Create a CLI command:

- `core/bin/run-workflow <workflow> <prompt>`

Arguments:

- `workflow`: workflow JSON path (relative to `core/workflows/` or absolute path under that root).
- `prompt`: workflow instruction text (`workflow_prompt`).

## 2. Current Status vs Planned Scope

Current implemented scope:

- Workflow editor, validation, and save/load APIs are implemented.
- Graph constraints are enforced in `core/engine/workflow_editor_utils.py`.

Planned in this document:

- Runtime workflow execution (`run-workflow`) is not implemented yet.
- This file is the execution requirement/design for implementation.

## 3. Runtime Entry and Engine Integration

1. `run-workflow` loads and validates the workflow JSON.
2. CLI sends execution request to core engine via `.skillpilot/temp/engine.sock`.
3. Engine executes nodes according to directed graph dependencies.
4. Each Agent node is executed through `core/bin/skill-agent`.

## 4. Execution Model (Directed Graph)

Treat workflow as DAG `G = (V, E)`:

- `V`: `Start`, `Agent`, `End`
- `E`: directed edges `source -> target`

Execution rules:

1. `Start` is orchestration-only and is not executed as an agent.
2. `Agent` runs only when all upstream Agent dependencies are finished.
3. `End` is orchestration-only; workflow completes when all nodes that can reach `End` are finished and `End` is satisfied.
4. If multiple Agents are dependency-ready at the same time, they may run in parallel.
5. If graph contains cycle or invalid structure, fail before runtime.

## 5. Agent Input Construction

For each Agent node `N`:

1. Collect upstream Agent outputs from all immediate input nodes.
2. Ignore `Start` as content input.
3. Build runtime prompt in this format:

```text
You are running as a Agent inside a multi-step workflow.

Workflow name: {workflow_name}
Current Agent: {current_agent_name}
Current Agent skill: {agent_skill}
Current Agent role: {agent_responsibility}  ← omitted if empty

Global workflow instruction:
{workflow_prompt}

Upstream inputs from directly connected Agents:
[from:{upstream_agent_name_1}]
Role: {upstream_role_description_1}  ← omitted if empty
Output: {upstream_output_1}

[from:{upstream_agent_name_2}]
Role: {upstream_role_description_2}  ← omitted if empty
Output: {upstream_output_2}
...

Task:
1. Complete the work required by your current Agent skill.
2. Use the global workflow instruction plus upstream inputs as context.
3. Return a concise, structured result that downstream Agents can consume directly.
4. If inputs are missing or conflicting, state assumptions clearly before your final output.
```

Notes:
- `agent_responsibility` is the optional free-text description of what the current Agent is responsible for. Include it in the prompt only when it is non-empty.
- `upstream_role_description` is the `responsibility` field from the upstream Agent node. Include the `Role:` line only when it is non-empty.

4. Execute with the node's configured provider and skill metadata.

## 6. Scheduling Algorithm

Recommended algorithm:

1. Build `indegree` for executable Agent dependencies.
2. Initialize ready queue with Agents whose required upstream Agents are complete.
3. Execute ready nodes (parallel-safe worker pool).
4. Store each node output in `node_output[node_id]`.
5. Decrement downstream dependency counts and enqueue newly ready nodes.
6. Finish when no runnable nodes remain and `End` is reachable/completed.

## 7. Output and Error Behavior

Success output:

- Execution summary (workflow path, run id, duration, node statuses).
- Final outputs from upstream nodes that feed into `End`.

Failure output:

- Fail-fast for invalid workflow schema/graph.
- Node-level runtime errors must include: `node_id`, `skill`, and error message.
- If one branch fails, mark dependent downstream nodes as blocked and return clear status.

## 8. Minimal CLI Contract

Example:

```bash
core/bin/run-workflow core/workflows/customer-support-flow.json "Handle this customer escalation"
```

Exit code:

- `0`: success
- non-zero: validation/runtime/system failure

## 9. Implementation Notes

- Reuse existing workflow validation before execution.
- Keep runtime prompt assembly deterministic for reproducibility.
- Keep filename and path rules consistent with `workflows/save` behavior (`xx-xx-xx.json`, lowercase kebab-case).
