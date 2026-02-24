# Workflow Feature Technical Design

Requirement reference:
- `core/development/workflows/requirement.md`

Plan reference:
- `core/development/workflows/plan.md`

## 1. Architecture Overview

Feature layers:
1. WebUI (`core/webui`)
   - Navigation entry and workflow page
   - Graph editor canvas and node/edge interactions
2. Engine API (`core/engine/routes.py`)
   - Tree/latest/content/validate/save workflow endpoints
3. Domain utilities (`core/engine/workflow_editor_utils.py`)
   - path safety
   - file naming and collision rules
   - graph validation logic
4. Storage (`core/workflows/`)
   - persisted workflow JSON files

## 2. Data Model

### 2.1 Workflow document

```json
{
  "version": "1.0",
  "name": "customer-support-flow",
  "updated_at": "2026-02-19T10:00:00Z",
  "nodes": [
    { "id": 0, "type": "start", "position": { "x": 120, "y": 260 } },
    {
      "id": 1,
      "type": "agent",
      "position": { "x": 420, "y": 260 },
      "data": {
        "title": "Classifier",
        "provider_id": "openai:gpt-4.1",
        "skill": "dev-swarm-code-review"
      }
    },
    { "id": -1, "type": "end", "position": { "x": 720, "y": 260 } }
  ],
  "edges": [
    { "id": "0->1", "source": 0, "target": 1 },
    { "id": "1->-1", "source": 1, "target": -1 }
  ]
}
```

### 2.2 Filename normalization

Input display name -> normalized file base name:
- lowercase
- trim spaces
- replace whitespace/underscore with `-`
- remove invalid chars
- collapse repeated `-`
- append `.json`

Collision handling:
- if `name.json` exists, use `name-2.json`, `name-3.json`, ...

## 3. Backend API Design

All APIs are under `/api`.

### 3.1 GET `/api/workflows/tree`

Response:
```json
{
  "items": [
    { "name": "support", "path": "support", "type": "dir", "mtime": 1739930400, "children": [] },
    { "name": "customer-support-flow.json", "path": "customer-support-flow.json", "type": "file", "mtime": 1739930500 }
  ]
}
```

### 3.2 GET `/api/workflows/latest`

Response:
```json
{ "path": "customer-support-flow.json" }
```

When empty:
```json
{ "path": null }
```

### 3.3 GET `/api/workflows/content?workflow=...`

Response:
```json
{
  "path": "customer-support-flow.json",
  "content": {
    "version": "1.0",
    "name": "customer-support-flow",
    "updated_at": "2026-02-19T10:00:00Z",
    "nodes": [],
    "edges": []
  }
}
```

### 3.4 POST `/api/workflows/validate`

Request:
```json
{
  "workflow": {
    "version": "1.0",
    "name": "customer-support-flow",
    "updated_at": "2026-02-19T10:00:00Z",
    "nodes": [],
    "edges": []
  }
}
```

Response (pass):
```json
{ "valid": true, "errors": [] }
```

Response (fail):
```json
{
  "valid": false,
  "errors": [
    {
      "rule": "DEGREE_SUBAGENT",
      "message": "Agent requires at least one outgoing link.",
      "node_ids": [3],
      "edge_ids": [],
      "suggestion": "Add a link from node 3 to another node toward End."
    }
  ]
}
```

### 3.5 POST `/api/workflows/save`

Request:
```json
{
  "filename": "customer-support-flow",
  "workflow": {
    "version": "1.0",
    "name": "Customer Support Flow",
    "updated_at": "2026-02-19T10:00:00Z",
    "nodes": [],
    "edges": []
  }
}
```

Response (success):
```json
{
  "status": "ok",
  "path": "customer-support-flow-2.json",
  "saved_name": "customer-support-flow-2.json"
}
```

Response (validation error): same shape as `/validate` with `status: "error"`.

## 4. Backend Validation Design

Validation order must match requirement section 3.

### 4.1 Steps

1. Structural checks
   - single `Start` and single `End`
   - unique node IDs
   - no self-loop
   - no duplicate source-target edge pair
2. Degree checks
   - enforce indegree/outdegree rules by type
3. Reachability checks
   - BFS/DFS from `Start` over forward graph
   - BFS/DFS from `End` over reversed graph
4. Cycle detection
   - Kahn topological sort on directed graph
   - if visited count < node count, cycle exists
5. Path existence
   - verify `End` reachable from `Start`

### 4.2 Error model

Each error item:
```json
{
  "rule": "RULE_CODE",
  "message": "Human-readable message",
  "node_ids": [1, 2],
  "edge_ids": ["1->2"],
  "suggestion": "How to fix"
}
```

## 5. Frontend Design

### 5.1 Page structure

Route: `/workflows`

Layout:
1. Left panel
   - tree view from `/api/workflows/tree`
   - `New Workflow` button
2. Right panel
   - workflow editor
   - top actions: `New Agent`, `Save Workflow`

### 5.2 Editor state model

Core state:
- `workflowPath: string | null`
- `workflowDoc: WorkflowDocument`
- `nodes: Node[]`
- `edges: Edge[]`
- `selectedEdgeId: string | null`
- `dirty: boolean`
- `saving: boolean`
- `errors: ValidationError[]`

### 5.3 Interaction rules

1. New workflow initializes default graph: `0 -> 1 -> -1`.
2. Dragging nodes updates position continuously with pointer movement.
3. Connecting anchors creates directed edge.
4. Clicking edge selects it and shows midpoint delete control.
5. Deleting selected edge updates graph immediately.
6. Saving triggers backend validation/save and shows errors or success.

### 5.4 Skills and providers

1. Load providers from existing provider API.
2. Load skills from `/api/config/skills` and flatten to autocomplete options.
3. `Agent.skill` is required before save.

## 6. Component/Module Design

### 6.1 Backend

New module: `core/engine/workflow_editor_utils.py`

Planned functions:
- `safe_workflow_path(path: str) -> Path`
- `build_workflow_tree(root: Path) -> list[dict]`
- `find_latest_workflow(root: Path) -> str | None`
- `normalize_workflow_filename(name: str) -> str`
- `resolve_filename_collision(root: Path, filename: str) -> str`
- `validate_workflow_doc(doc: dict) -> list[dict]`

### 6.2 Frontend

New folder: `core/webui/components/workflows/`

Planned components:
- `workflow-sidebar.tsx`
- `workflow-editor.tsx`
- `agent-node.tsx`
- `validation-panel.tsx`
- `use-workflow-editor.ts` (state/actions hook)

## 7. UX and Visual Design Constraints

1. Match existing light theme.
2. Full-height editor area inside page shell.
3. Canvas scroll both directions.
4. Node card auto-sizing for title/provider/skill rows.
5. Error presentation should be clear and actionable.

## 8. Testing Design

### 8.1 Backend

1. Unit tests for filename normalization/collision.
2. Unit tests for each validation rule.
3. API tests for tree/latest/content/validate/save.

### 8.2 Frontend

1. Manual scenario checks:
   - create default workflow
   - add node
   - connect/disconnect
   - drag node
   - save pass/fail
2. Optional UI tests for key editor flows.

## 9. Rollout and Compatibility

1. Non-breaking: existing `Courses` and `Skills` flows unchanged.
2. New `Workflows` page is additive.
3. Invalid old workflow files (if any) should open with validation errors, not crash.

## 10. Final Design Decisions

1. Graph library: use React Flow (`@xyflow/react`) for canvas, dragging, and edge interactions.
2. API versioning: keep `/api/workflows/*` only in this phase (no alias routes).
3. Folder creation from UI: out of scope for this phase.
