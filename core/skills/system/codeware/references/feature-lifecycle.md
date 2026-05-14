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
The `update/fix` stage only sets up the trigger doc. `plan` and `implement` then run the same as in Flow 1, but automatically read the trigger doc for context.

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

`plan.md` is shared across all flows and archived before each new plan. Trigger docs are archived when a new cycle starts:

| File | When archived |
|------|--------------|
| `plan.md` | Before writing a new plan (all flows) |
| `update.md` | When `update feature` is called again for a new cycle |
| `issues.md` | When `fix issues` is called again for a new cycle |

Archive files go under `core/development/{feature-name}/archive/` as `{basename}.{YYYY-MM-DD-HHMM}.md`.

---

## Feature Folder Layout

```
core/development/{feature-name}/
├── README.md              # persistent
├── CHANGELOG.md           # persistent
├── AGENTS.md              # persistent
├── requirements.md        # persistent
├── implementation.md      # persistent
├── plan.md                # shared across all flows
├── update.md              # update flow trigger doc
├── issues.md              # fix flow trigger doc
└── archive/
    ├── plan.{timestamp}.md
    ├── update.{timestamp}.md
    └── issues.{timestamp}.md
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
