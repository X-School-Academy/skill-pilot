# Feature Retrieval Index: Workflow Runner and Editor

## Retrieval Keywords

workflow, workflow runner, workflow editor, workflow execution, run-workflow, agent-workflow, workflow JSON, workflow node, workflow continue, workflow validate, workflow status, workflow save, workflow delete, workflow tree, workflow execute, course-plan-and-schedule, research-multi-agent, vibe-coding-dev, skill-pilot-dev, workflow_editor_utils, workflow_execution, run_workflow

## Scope

- JSON-based workflow definition, validation, execution, and continuation
- Workflow file tree and content management in the engine
- Web UI workflow editor and status page
- Predefined workflow templates under `core/workflows/`
- Excludes: individual skill execution (see skill agent feature)

## Main Behavior

- `GET /api/workflows/tree` and `/latest` return workflow file structure
- `GET /api/workflows/content` returns a workflow JSON file
- `POST /api/workflows/execute` starts a workflow run
- `GET /api/workflows/execute/status` polls execution state
- `POST /api/workflows/execute/continue` resumes a waiting node
- `POST /api/workflows/validate` validates a workflow JSON
- `POST /api/workflows/save` and `/delete` manage workflow files
- CLI entry point: `core/bin/run-workflow`

## Code Map

- `core/engine/routes.py` — `/api/workflows/*` route handlers
- `core/engine/workflow/` — workflow engine: `VideoStyle.py`, `course_planner.py`, `llm_adapter.py`, `video_creator.py`, `video_utils/`
- `core/engine/workflow_editor_utils.py` — workflow JSON editing utilities
- `core/engine/mcp_servers/mcp_to_skills/workflow_execution.py` — skill-level workflow execution
- `core/engine/mcp_servers/mcp_to_skills/run_workflow.py` — run_workflow MCP action
- `core/bin/run-workflow` — CLI runner
- `core/workflows/` — bundled workflow templates: `course-plan-and-schedule.json`, `research-multi-agent.json`, `vibe-coding-dev.json`, `skill-pilot-dev.json`, `test-number-workflow.json`
- `core/webui/pages/workflows/index.tsx` — workflow editor/runner page

## Search Commands

```bash
rg "api/workflows" core/engine/routes.py -n
rg "workflow_execution" core/engine/ -l
find core/workflows/ -name "*.json"
rg "run.workflow" core/bin/ -l
```

## Related Features

- `core/features/skill-agent-system.md`
- `core/features/vibe-coding-project-manager.md`
- `core/features/course-creator.md`

## Update Notes

- `execute/continue` requires the execution ID from the initial execute response
- Workflow JSON schema must remain compatible with existing templates in `core/workflows/`
- Test: run `core/bin/run-workflow` with `test-number-workflow.json` as smoke test
