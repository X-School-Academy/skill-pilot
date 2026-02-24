# Workflow Feature Requirement

In the WebUI, add a new menu item `Workflows` near the `Skills` menu.

Once clicked, the page layout should be similar to `Courses`.

## 1. Page Layout

1. Left navigation panel:
   - Show all folders and workflow JSON files under `core/workflows/`.
   - Folder order and display style should match the `Courses` navigation.
2. Right main panel:
   - Show the latest updated workflow by default.
   - If no workflow exists, show the create-new-workflow state.
3. Add a button `New Workflow` above the workflow list in the left navigation.
4. Workflow filename rule:
   - Use lowercase kebab-case JSON names: `xx-xx-xx.json`.
   - Allowed characters: `a-z`, `0-9`, `-`
   - Regex: `^[a-z0-9]+(?:-[a-z0-9]+)*\.json$`
   - Example: `customer-support-flow.json`
   - If the same filename already exists, auto-suffix with `-2`, `-3`, ... before `.json`.
   - Example: `customer-support-flow-2.json`
5. Clicking `New Workflow` or an existing workflow opens the Workflow Editor in the right panel.

## 2. Workflow Editor

1. Node types: `Start`, `Agent`, `End`.
2. New workflow default graph: `Start -> Agent -> End`.
3. `Start` and `End` cannot be deleted.
4. `Start` node rules:
   - Exactly 0 incoming links.
   - One or more outgoing links.
5. `End` node rules:
   - One or more incoming links.
   - Exactly 0 outgoing links.
6. `Agent` node rules:
   - One or more incoming links.
   - One or more outgoing links.
7. Node IDs must be unique:
   - `Start`: `0`
   - `End`: `-1`
   - `Agent`: positive integers (`1, 2, 3, ...`)
8. All nodes are draggable and can be moved freely by mouse on the workflow editor canvas.
9. Each `Agent` has:
   - Editable title/name.
   - LLM provider selector (options from all available provider IDs).
   - Default provider uses the default AI Provider configured in AI & Security.
   - Skill text input with auto-complete from available agent skill names.
10. `Agent` node card auto-resizes to fit title, provider, and skill rows.
11. Connection anchors:
   - Each `Agent` has 4 anchors (middle of top/right/bottom/left).
   - Each anchor can create one-to-many directed links.
   - `Start` has one outgoing anchor only.
   - `End` has one incoming anchor only.
12. Top-left editor control: `New Agent` button:
   - Click: create a new `Agent` node.
   - Drag (optional UX): create and place a new node.
13. Top-right editor control: `Save Workflow` button:
   - Save node metadata, coordinates, and directed links.
   - Persist to JSON in `core/workflows/` via new workflow APIs in `core/engine/`.

## 3. Graph Model and Save Validation (Important)

Treat each workflow as a directed graph `G = (V, E)`:
- `V`: all nodes (`Start`, `Agent`, `End`)
- `E`: directed links (`from_node_id -> to_node_id`)

On `Save Workflow`, run validation in this order:

1. Structural validation
   - Node IDs are unique and valid by type rules.
   - `Start` and `End` both exist exactly once.
   - No self-loop (`u -> u`).
   - No duplicate edge (`u -> v` repeated).

2. Degree-rule validation
   - `Start`: indegree `= 0`, outdegree `>= 1`.
   - `End`: indegree `>= 1`, outdegree `= 0`.
   - Every `Agent`: indegree `>= 1` and outdegree `>= 1`.

3. Reachability validation
   - Forward traversal (DFS/BFS) from `Start` must reach every node.
   - Reverse traversal from `End` (or traversal on reverse graph) must reach every node.
   - This guarantees no orphan node/group and ensures each node is on some path from `Start` to `End`.

4. Cycle/dead-loop validation
   - The graph must not contain a directed cycle.
   - Use topological sort (Kahn) or DFS color marking.
   - If a cycle exists, reject save with node IDs participating in the cycle.

5. Path existence validation
   - At least one valid directed path must exist from `Start` to `End`.

Validation result behavior:
- If any check fails: block save and show clear error messages.
- If all checks pass: persist workflow JSON.

## 4. Error Message Requirements

1. Error text must clearly include:
   - Validation rule name.
   - Problem node ID(s) and/or edge(s).
   - Suggested fix action.
2. Multiple errors should be shown together when possible (not fail-fast on first error only).

## 5. Workflow JSON Schema Contract

Use one shared contract for frontend and backend validation.

### 5.1 File shape

Each workflow JSON file must match:

```json
{
  "version": "1.0",
  "name": "customer-support-flow",
  "updated_at": "2026-02-19T10:00:00Z",
  "nodes": [],
  "edges": []
}
```

Required top-level fields:
- `version` (string): schema version (current: `1.0`)
- `name` (string): workflow display name (not filename)
- `updated_at` (string): ISO-8601 UTC timestamp
- `nodes` (array): all graph nodes
- `edges` (array): all directed links

### 5.2 Node object contract

```json
{
  "id": 1,
  "type": "agent",
  "position": { "x": 420, "y": 240 },
  "data": {
    "title": "Review Agent",
    "provider_id": "claude",
    "skill": "dev-swarm-code-review"
  }
}
```

Rules:
- `id` (integer)
  - `0` for `start`
  - `-1` for `end`
  - positive integer for `agent`
- `type` (enum): `start`, `agent`, `end`
- `position.x`, `position.y` (number): canvas coordinates
- `data` object:
  - `agent`: required with fields:
    - `title` (string, min length 1)
    - `provider_id` (string, min length 1)
    - `skill` (string, min length 1)
  - `start` / `end`: data should be omitted or empty object

### 5.3 Edge object contract

```json
{
  "id": "1->2",
  "source": 1,
  "target": 2
}
```

Rules:
- `id` (string): unique edge ID (recommended format: `source->target[#index]`)
- `source` (integer): source node ID
- `target` (integer): target node ID
- `source` and `target` must reference existing node IDs

### 5.4 Base JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "workflow.schema.json",
  "title": "Workflow",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "name", "updated_at", "nodes", "edges"],
  "properties": {
    "version": { "type": "string", "const": "1.0" },
    "name": { "type": "string", "minLength": 1 },
    "updated_at": { "type": "string", "format": "date-time" },
    "nodes": {
      "type": "array",
      "minItems": 3,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "type", "position"],
        "properties": {
          "id": { "type": "integer" },
          "type": { "type": "string", "enum": ["start", "agent", "end"] },
          "position": {
            "type": "object",
            "additionalProperties": false,
            "required": ["x", "y"],
            "properties": {
              "x": { "type": "number" },
              "y": { "type": "number" }
            }
          },
          "data": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "title": { "type": "string", "minLength": 1 },
              "provider_id": { "type": "string", "minLength": 1 },
              "skill": { "type": "string", "minLength": 1 }
            }
          }
        },
        "allOf": [
          {
            "if": { "properties": { "type": { "const": "start" } }, "required": ["type"] },
            "then": { "properties": { "id": { "const": 0 } } }
          },
          {
            "if": { "properties": { "type": { "const": "end" } }, "required": ["type"] },
            "then": { "properties": { "id": { "const": -1 } } }
          },
          {
            "if": { "properties": { "type": { "const": "agent" } }, "required": ["type"] },
            "then": {
              "properties": { "id": { "type": "integer", "minimum": 1 } },
              "required": ["data"],
              "allOf": [
                { "properties": { "data": { "required": ["title", "provider_id", "skill"] } } }
              ]
            }
          }
        ]
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "source", "target"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "source": { "type": "integer" },
          "target": { "type": "integer" }
        }
      }
    }
  }
}
```

### 5.5 Semantic checks not covered by JSON Schema

The base schema checks shape and basic type constraints only. Backend must still enforce Section 3 graph validations:
- unique node IDs and unique edge pairs
- no self-loop
- degree rules by node type
- full reachability from `Start` and to `End`
- no directed cycle
- at least one `Start -> End` path

### Theme/style

Match the current light theme design.

### Others

1. `skill` is required for each `Agent`.
2. While dragging a node, the node position should follow the mouse pointer coordinates.
3. Clicking a link should show a delete icon at link midpoint; clicking the icon deletes the link.
4. The canvas should use full screen height and support both horizontal and vertical scrolling.
