---
name: create-update-agent-workflow
description: Create or update agent workflow JSON files under core/workflows using the project's workflow schema and validation rules. Use when the user asks to create, fix, review, or update a workflow file for the workflow editor or workflow execution.
---

# AI Builder - Create/Update Agent Workflow

This skill creates or updates workflow JSON files that the WebUI and backend workflow engine can load, validate, save, and execute.

## When to Use This Skill

- The user asks to create a new workflow JSON
- The user asks to update an existing workflow JSON
- The user wants to fix workflow validation errors
- The user wants to convert a process into a workflow graph for `core/workflows/`

## Your Roles in This Skill

- **Project Manager**: Translate the user's requested process into a valid step-by-step workflow graph with clear dependencies.
- **Backend Developer (Engineer)**: Apply the exact workflow schema and validation rules used by the backend.
- **QA Engineer**: Check for format errors, broken references, unreachable nodes, and loops before finishing.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Determine the Target File

1. If the user provides an existing workflow file path, update that file.
2. If the user does not provide a file path, create a new workflow JSON under `core/workflows/`.
3. Use a lowercase kebab-case filename ending in `.json`.
4. Keep the workflow path under `core/workflows/`. Do not write workflow files outside that tree unless the user explicitly requests it.

### Step 2: Collect the Workflow Shape

1. Identify the workflow name.
2. Identify each agent step the user wants.
3. Identify the dependency order between steps.
4. Convert the dependency order into a directed acyclic graph that starts at Start and ends at End.
5. Use `references/sample.json` as a format-only reference when helpful.

### Step 3: Build a Valid Workflow Document

Create a JSON object with this top-level structure:

- `version`: string, normally `1.0`
- `name`: workflow name string
- `updated_at`: ISO UTC timestamp string if you are updating or regenerating the file
- `nodes`: array
- `edges`: array

Use these node rules:

1. Include exactly one Start node:
   - `id` must be `0`
   - `type` must be `start`
   - `position` must include numeric `x` and `y`
2. Include exactly one End node:
   - `id` must be `-1`
   - `type` must be `end`
   - `position` must include numeric `x` and `y`
3. Each agent node must:
   - use `type: "agent"`
   - use a positive integer `id`
   - include numeric `position.x` and `position.y`
   - include `data.title` as a non-empty string
   - include `data.provider_id` as a non-empty string
   - include at least one non-empty field between `data.skill` and `data.responsibility`
4. Keep every node id unique.

Use these edge rules:

1. Each edge must include:
   - `id` as a non-empty unique string
   - `source` as an integer node id
   - `target` as an integer node id
2. Every edge `source` and `target` must reference real existing node ids in the same file.
3. Each `(source, target)` pair must be unique.
4. Do not create self-loops.
5. When adding, removing, or renaming nodes, update related edges at the same time so there are no stale, broken, or mismatched node-edge relations.
6. Use anchors when practical for editor readability:
   - `source_anchor`
   - `target_anchor`

### Step 4: Enforce Workflow Graph Validity

Before saving, check all of the following:

1. Start must have:
   - indegree `0`
   - outdegree `>= 1`
2. End must have:
   - indegree `>= 1`
   - outdegree `0`
3. Every agent node must have:
   - indegree `>= 1`
   - outdegree `>= 1`
4. Every node must be reachable from Start.
5. Every node must have a path to End.
6. The graph must be acyclic.
7. At least one valid path from Start to End must exist.
8. Every dependency relation in the requested process must be represented by the correct edge direction.
9. If multiple upstream nodes feed one downstream node, make sure the merge node keeps all required incoming edges.

If any of these checks fail, fix the graph before returning the result.

### Step 5: Validate Agent Skill Names

1. If an agent node uses `data.skill`, make sure the skill name is the actual skill name, not a descriptive sentence.
2. Use the exact installed skill name format, for example `create-update-agent-skill`, not a title-cased or spaced variant.
3. If the correct skill name is unclear, keep `data.skill` empty and put the instruction in `data.responsibility` instead of inventing an incorrect skill name.
4. Do not leave both `data.skill` and `data.responsibility` empty.

### Step 6: Save or Update the File

1. If creating a new workflow, save it under `core/workflows/<workflow-name>.json` unless the user requests a different path inside `core/workflows/`.
2. If updating an existing workflow, preserve the same file unless the user explicitly asks to rename it.
3. Keep the JSON pretty-printed with two-space indentation.
4. End the file with a trailing newline.

### Step 7: Final Review

Before finishing, verify:

1. The JSON is syntactically valid.
2. The workflow follows the rules in `references/workflow-validation-rules.md`.
3. There is no dead loop or cycle.
4. Start is `0`, End is `-1`, and all agent ids are positive integers.
5. The agent skill names are valid-looking and consistently formatted.
6. All edge relations still match the final node list, with no broken references or stale connections.

## Expected Output

- A created or updated workflow JSON file
- A short note describing the file path and the main workflow steps
- Any assumption that affected node structure, provider choice, or skill naming

## Key Principles

- Follow the backend validator rules exactly
- Prefer simple, readable graphs over clever graph layouts
- Do not invent invalid skill names
- Do not create loops, orphan nodes, or unreachable branches
- Keep node-edge relations synchronized whenever the workflow changes
- Default new workflows to `core/workflows/`

## Common Issues

**Issue: Start or End node is missing**
- Solution: Always include exactly one Start (`id: 0`) and one End (`id: -1`) node.

**Issue: Agent node fails validation**
- Solution: Ensure every agent node has a positive integer id, a title, a provider id, and at least one of `skill` or `responsibility`.

**Issue: Workflow has a dead loop**
- Solution: Remove the cycle and make the graph a DAG before saving.

**Issue: Nodes are disconnected**
- Solution: Ensure every node is reachable from Start and can reach End.

**Issue: Edge relations are broken after editing nodes**
- Solution: Rebuild or update all affected edges whenever nodes are added, removed, reordered, or merged so every edge still points to valid node ids and matches the intended dependency flow.

**Issue: Skill name is not real**
- Solution: Use the exact installed skill name, or leave `skill` empty and use `responsibility` until the correct skill name is known.
