# Feature Retrieval Index: Skill Pilot Development Feature Lifecycle

## Retrieval Keywords

skill-pilot-development, feature lifecycle, create feature, update request, issue report, feature list, development tree, development content, development save, development delete, development file, core/development, codeware feature, feature create, feature freeze, core/features, lifecycle, plan, implement, review, test, merge, freeze

## Scope

- Feature lifecycle management under `core/development/` (create, update, delete, issue report)
- Development file tree and content viewer for Skill Pilot's own features
- Frozen feature index management under `core/features/`
- Excludes: vibe coding projects, user task management (separate features)

## Main Behavior

- `GET /api/skill-pilot-development/features` lists features under `core/development/`
- `GET /api/skill-pilot-development/tree` returns directory tree
- `GET /api/skill-pilot-development/latest` returns most recently modified item
- `GET /api/skill-pilot-development/content` returns document content
- `POST /api/skill-pilot-development/save` saves document
- `POST /api/skill-pilot-development/create-feature` creates a new feature document set
- `POST /api/skill-pilot-development/create-update-request` creates an update request
- `POST /api/skill-pilot-development/create-issue-report` files an issue report
- `POST /api/skill-pilot-development/delete` removes a feature
- `GET /api/skill-pilot-development/file` serves a raw file
- Feature documents stored under `core/development/`

## Code Map

- `core/engine/routes.py` — `/api/skill-pilot-development/*` route handlers
- `core/webui/pages/skill-pilot-development/index.tsx` — development UI page
- `core/development/` — feature lifecycle documents
- `core/features/` — frozen feature retrieval index (this directory)
- `core/skills/system/codeware/` — codeware skill with lifecycle reference docs
- `core/skills/system/codeware/references/feature-lifecycle.md` — lifecycle process doc
- `core/skills/system/codeware/references/feature-lifecycle-freeze.md` — freeze step doc
- `core/skills/system/skill-pilot-freeze-core-feature/SKILL.md` — freeze skill

## Search Commands

```bash
rg "api/skill-pilot-development" core/engine/routes.py -n
find core/development/ -type f -name "*.md"
find core/features/ -type f -name "*.md"
find core/skills/system/codeware/ -type f
```

## Related Features

- `core/features/codeware-dev-mode.md`
- `core/features/workflow-runner-editor.md`

## Update Notes

- `core/development/` stores in-progress feature work; `core/features/` stores frozen retrieval indexes
- Freeze step should run after a successful feature merge
- Feature file naming in `core/features/` must be keyword-rich lowercase kebab-case
