# Feature Retrieval Index: Dev Swarm Software Lifecycle

## Retrieval Keywords

dev swarm, dev-swarm, software lifecycle, AI agile, feature-driven development, sprints, PRD, UX, tech specs, MVP, deployment, market research, personas, tech research, stage, dev swarm skills, dev-swarm-stage, vibe kanban, dev swarm code development, dev swarm code review, dev swarm code test, dev swarm agent

## Scope

- Full software lifecycle management via AI agent swarm
- Stage-based skills: init ideas, market research, personas, UX, PRD, tech research, tech specs, MVP, sprints, deployment, archive
- Dev swarm workflow coordination
- Excludes: vibe coding (simpler project flow), task manager (separate)

## Main Behavior

- Dev swarm coordinates multiple stage skills to take a product from idea to deployment
- Each stage is a skill in `dev-swarm/skills/`
- `dev-swarm-code-development` handles implementation sprints
- `dev-swarm-code-review` handles code review
- `dev-swarm-code-test` handles test writing
- `dev-swarm-stage-*` skills cover each lifecycle stage
- Vibe Kanban extension provides Kanban board for sprint tracking
- Multi-agent research workflow coordinates parallel research tasks

## Code Map

- `dev-swarm/skills/` — all dev swarm stage skills
- `dev-swarm/skills/dev-swarm-code-development/` — code development skill
- `dev-swarm/skills/dev-swarm-code-review/` — code review skill
- `dev-swarm/skills/dev-swarm-code-test/` — test writing skill
- `dev-swarm/skills/dev-swarm-stage-init-ideas/` — idea initialization stage
- `dev-swarm/skills/dev-swarm-stage-market-research/` — market research stage
- `dev-swarm/skills/dev-swarm-stage-personas/` — user personas stage
- `dev-swarm/skills/dev-swarm-stage-ux/` — UX stage
- `dev-swarm/skills/dev-swarm-stage-prd/` — PRD stage
- `dev-swarm/skills/dev-swarm-stage-tech-research/` — tech research stage
- `dev-swarm/skills/dev-swarm-stage-tech-specs/` — tech specs stage
- `dev-swarm/skills/dev-swarm-stage-mvp/` — MVP stage
- `dev-swarm/skills/dev-swarm-stage-sprints/` — sprints stage
- `dev-swarm/skills/dev-swarm-stage-deployment/` — deployment stage
- `dev-swarm/skills/dev-swarm-stage-archive/` — archive stage
- `dev-swarm/skills/dev-swarm-stage-architecture/` — architecture stage
- `dev-swarm/docs/ai-agile-development.md` — agile development guide
- `dev-swarm/docs/ai-feature-driven-development.md` — feature-driven development guide
- `core/engine/dev_swarm/` — dev swarm engine: `agent.py`, `documents.py`, `project.py`, `router.py`, `stages.py`
- `core/webui/pages/dev-swarm/` — dev swarm web UI
- `extensions/vibe-kanban/` — Vibe Kanban extension

## Search Commands

```bash
find dev-swarm/skills/ -name "SKILL.md" | head -20
find core/engine/dev_swarm/ -type f
cat dev-swarm/docs/ai-agile-development.md | head -40
find extensions/vibe-kanban/ -type f | head -10
```

## Related Features

- `core/features/vibe-coding-project-manager.md`
- `core/features/research-manager.md`
- `core/features/agent-cli.md`
- `core/features/workflow-runner-editor.md`

## Update Notes

- Dev swarm stages run sequentially; each stage produces documents consumed by the next
- `dev-swarm/` directory contains user-facing product documents; preserve on upgrades
- `core/engine/dev_swarm/stages.py` defines stage ordering and transitions
