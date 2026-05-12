# Feature Lifecycle Index

Use this reference as the map for feature work under `core/development/`. After identifying the requested action, load only the matching action reference.

---

## Default Flows

### Flow 1: New Feature
```
create → refine → initial → plan → implement → test → review → merge → freeze
```

### Flow 2: Update or Bug Fix (existing feature)
```
update/fix → refine → initial (new branch) → plan → implement → test → review → merge → freeze
```

### Flow 3: Under Agent-Workflow
Same sequence as Flow 1 or Flow 2. After each step completes, also invoke the `agent-workflow` skill's continue-workflow action. See `references/feature-lifecycle-agent-workflow.md`.

---

## Persistent Files

These five files are created at `create` time and kept up to date throughout all stages:

- `README.md` — feature overview and usage
- `CHANGELOG.md` — log of changes per update/fix cycle
- `AGENTS.md` — AI-agent instructions for this feature
- `requirements.md` — living requirements document
- `implementation.md` — living implementation summary

---

## Working Docs and Archive Convention

Per-cycle working docs are specific to each flow and archived before a new cycle starts:

| Flow | Working docs | Archived as |
|------|-------------|-------------|
| New feature | `plan.md` | `archive/plan.{timestamp}.md` |
| Update | `update.md`, `update-plan.md`, `update-impl.md` | `archive/update.{timestamp}.md`, etc. |
| Fix | `issues.md`, `issues-plan.md`, `issues-impl.md` | `archive/issues.{timestamp}.md`, etc. |

Archive files go under `core/development/{feature-name}/archive/`.

---

## Feature Folder Layout

```
core/development/{feature-name}/
├── README.md
├── CHANGELOG.md
├── AGENTS.md
├── requirements.md
├── implementation.md
├── plan.md                    # new feature flow
├── update.md                  # update flow
├── update-plan.md
├── update-impl.md
├── issues.md                  # fix flow
├── issues-plan.md
├── issues-impl.md
└── archive/
    ├── plan.{timestamp}.md
    ├── update.{timestamp}.md
    ├── update-plan.{timestamp}.md
    ├── update-impl.{timestamp}.md
    ├── issues.{timestamp}.md
    ├── issues-plan.{timestamp}.md
    └── issues-impl.{timestamp}.md
```

---

## Shared Context Rules

- A feature's `requirements.md` may list related feature files under `core/features/`.
- Read only the mentioned related feature files for context. Do not read all files in `core/features/`.
- If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

---

## Action Map

- `create`: use `references/feature-lifecycle-create.md`
- `refine`: use `references/feature-lifecycle-refine.md`
- `initial`: use `references/feature-lifecycle-initial.md`
- `plan`: use `references/feature-lifecycle-plan.md`
- `implement`: use `references/feature-lifecycle-implement.md`
- `review`: use `references/feature-lifecycle-review.md`
- `test`: use `references/feature-lifecycle-test.md`
- `merge`: use `references/feature-lifecycle-merge.md`
- `freeze`: use `references/feature-lifecycle-freeze.md`
- `update feature`: use `references/feature-lifecycle-update.md`
- `fix issues`: use `references/feature-lifecycle-fix-issues.md`
- agent-workflow context: use `references/feature-lifecycle-agent-workflow.md`
