# Dev Swarm

## Brief

Commercial product workspace for running a staged product-building flow from idea definition through deployment.

## User Value

- Makes the commercial project lifecycle visible and repeatable.
- Connects each stage to purpose-built prompts and agent skills.
- Keeps stage documents, previews, and execution output together.

## Main Behavior

- Organizes work by product stage such as init ideas, market research, personas, MVP, PRD, UX, architecture, tech specs, devops, sprints, and deployment.
- Shows per-stage actions like creating proposals, files, plans, backlogs, mockups, and research runs.
- Streams execution output and supports document preview, deletion, and stage navigation.
- Uses stage-aware prompts to orchestrate development work.

## Related Features

- `platform-shell-and-navigation.md`
- `tasks.md`
- `workflows.md`
- `skills-management.md`

## Code References

- `core/webui/pages/dev-swarm/index.tsx`
- `core/engine/dev_swarm/router.py`
- `core/engine/dev_swarm/project.py`
- `core/engine/dev_swarm/stages.py`
- `core/engine/dev_swarm/documents.py`
- `core/engine/dev_swarm/agent.py`
- `dev-swarm/skills/dev-swarm-stage-init-ideas/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-market-research/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-personas/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-mvp/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-prd/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-ux/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-architecture/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-tech-research/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-tech-specs/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-devops/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-sprints/SKILL.md`
- `dev-swarm/skills/dev-swarm-stage-deployment/SKILL.md`
- Keywords: `renderActionButton`, `createEventSource`, `deleteDocument`, `stageConfig`, `prompts`

