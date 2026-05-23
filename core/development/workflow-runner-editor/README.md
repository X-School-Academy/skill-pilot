# Workflow Runner and Editor

## Overview

This feature provides Skill Pilot workflow authoring, validation, execution, continuation, and retrieval context.

Workflows are JSON documents stored under `core/workflows/`. Runnable workflow nodes use `type: "agent"` and select Skill Pilot subagents with `data.subagent`. Workflow execution can run through a managed tmux session, an existing tmux agent session, or the non-tmux background runner.

## User-Facing Entry Points

- Web UI workflow editor: `core/webui/pages/workflows/index.tsx`
- Engine workflow APIs: `/api/workflows/*`
- CLI runner: `core/bin/run-workflow`
- Agent skill: `core/skills/system/agent-workflow`
- Frozen retrieval index: `core/features/workflow-runner-editor.md`

## Core Behaviors

- Create and edit workflow JSON with Start, Agent, and End nodes.
- Select subagents from `core/subagents/*/*.md` through Web UI autocomplete.
- Validate workflow structure before saving or running.
- Execute workflows through:
  - managed tmux session `sp-workflow-execute`
  - existing tmux sessions detected through `TMUX_SESSION_NAME`
  - non-tmux background mode forced by `--tmux-session=none`
- Support `auto_continue` mode and `start_by_prompt` mode.
- Require node agents to write output files under the workflow output root.
- Keep node prompts scoped to the current node and upstream outputs.

## Documentation

- `requirements.md` records the reverse-engineered product and integration requirements.
- `implementation.md` summarizes the implemented code design and runtime behavior.
- `plan.md` records the development plan and known follow-up items.
- `AGENTS.md` gives future agents feature-specific maintenance instructions.
- `CHANGELOG.md` tracks lifecycle documentation changes.

