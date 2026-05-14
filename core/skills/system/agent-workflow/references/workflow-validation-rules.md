# Workflow Validation Rules

These rules mirror the backend validation used by `core/engine/workflow_editor_utils.py`.

## File and Shape

- The workflow document must be a JSON object.
- `nodes` must be an array.
- `edges` must be an array.

## Node Rules

- Every node must be an object.
- Every node must have an integer `id`.
- Every node must have a `position` object with finite numeric `x` and `y`.
- Node ids must be unique.

### Start Node

- Exactly one Start node is allowed.
- Start node `type` must be `start`.
- Start node `id` must be `0`.
- Start node must have:
  - indegree `0`
  - outdegree `>= 1`

### End Node

- Exactly one End node is allowed.
- End node `type` must be `end`.
- End node `id` must be `-1`.
- End node must have:
  - indegree `>= 1`
  - outdegree `0`

### Agent Nodes

- Agent node `type` must be `agent`.
- Agent id must be a positive integer.
- Agent node `data` must be an object.
- `data.title` must be a non-empty string.
- `data.provider_id` must be a non-empty string.
- At least one of these must be non-empty:
  - `data.skill`
  - `data.responsibility`
- Every agent node must have:
  - indegree `>= 1`
  - outdegree `>= 1`

## Edge Rules

- Every edge must be an object.
- Every edge must have a non-empty string `id`.
- Edge ids must be unique.
- `source` and `target` must be integer node ids.
- `source` and `target` must point to existing nodes.
- Self-loops are not allowed.
- Duplicate `(source, target)` edges are not allowed.

## Graph Rules

- All nodes must be reachable from Start.
- All nodes must have a path to End.
- The workflow graph must be acyclic.
- At least one path from Start to End must exist.

## Practical Naming Rules

- New workflow filenames should be lowercase kebab-case and end in `.json`.
- The WebUI launches workflow files from `core/workflows/`.
- Use exact agent skill names in `data.skill` when known.
