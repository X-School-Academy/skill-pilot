# Workflows

## Brief

Workflow builder and runner for graph-based agent workflows stored under `core/workflows`.

## User Value

- Lets users design reusable agent workflows visually.
- Supports validate, execute, continue, and save inside one tool.
- Reuses workflows across the home session launcher and workspace pages.

## Main Behavior

- Loads the workflow tree and selected workflow content.
- Edits graph nodes and edges for workflow definitions.
- Validates workflows before execution.
- Executes workflows and tracks execution status, including continue/resume behavior.
- Saves workflow JSON back into the project workflow library.

## Related Features

- `new-session.md`
- `tasks.md`
- `research.md`
- `vibe-coding.md`
- `skill-pilot-development.md`

## Code References

- `core/webui/pages/workflows/index.tsx`
- `core/engine/routes.py`
- `core/workflows/new-workflow.json`
- `core/workflows/setup-openclaw.json`
- `core/workflows/test-number-workflow.json`
- `core/skills/system/agent-workflow/SKILL.md`
- Keywords: `WorkflowsPage`, `removeSelectedEdge`, `execute`, `validate`, `continue`, `workflow graph`
- API routes: `/api/workflows/tree`, `/api/workflows/latest`, `/api/workflows/content`, `/api/workflows/execute/status`, `/api/workflows/execute`, `/api/workflows/execute/continue`, `/api/workflows/validate`, `/api/workflows/save`
