---
name: vibe-coding
description: Manage the full lifecycle of a Vibe Coding project — create, refine, brainstorm, initialize, plan, implement, review, test, deploy, update, and fix issues. Use when the user wants to start a new project from a prompt, evolve its requirements, plan or write code, validate or deploy it, or apply updates and bug fixes against an existing project.
---

# Vibe Coding Skill

Drives every stage of a Vibe Coding project. Stage details live in `references/`. This file defines layout, lifecycle rules, and stage dispatch.

## Roles

Project Manager · Technical Writer · Backend Developer · DevOps Engineer · Code Reviewer · QA Engineer · Creative Strategist

Apply only the roles relevant to the chosen stage. Announce actions before performing them: `As a {Role}, I will {action}.`

## Project Boundary

Stay inside `workspace/vibe-coding/{project-name}/` unless the user explicitly asks otherwise.

## Project Layout

```
workspace/vibe-coding/{project-name}/
├── README.md                 # overview and usage guide
├── CHANGELOG.md              # change log per update/fix cycle
├── AGENTS.md                 # AI-agent instructions for this project
├── design-docs/
│   ├── requirements.md       # living — scope and intent
│   ├── plan.md               # living — current implementation plan
│   ├── implementation.md     # living — current implementation summary
│   ├── deployment.md         # living — deployment record
│   ├── initialized.md        # write-once — init completed mark
│   └── archive/              # timestamped snapshots
└── (project source code)
```

`create` bootstraps all folders and top-level files. `deploy` creates `assets/` when missing.

## File Lifecycle Rules

**Living docs** (overwrite in place, always current): `requirements.md`, `plan.md`, `implementation.md`, `deployment.md`. Refresh after any stage that changes scope, plan, or code.

**Top-level files** (maintain throughout lifecycle):
- `README.md` — update when purpose, usage, or setup changes
- `CHANGELOG.md` — append an entry each update/fix cycle
- `AGENTS.md` — update when AI-agent notes change

**Plan archiving** — before writing a new `plan.md`, archive the old one:
```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/plan.md "design-docs/archive/plan.$timestamp.md"
```

**Intermediates** — archive after consumption using `{basename}.{YYYY-MM-DD-HHMM}.md`:
- Human-loop: `brainstorm.md`, `issues.md`, `update.md`, `reviewed.md`, `tested.md`
- Review-output: `issues-plan.md`, `issues-impl.md`, `update-plan.md`, `update-impl.md`

`initialized.md` is write-once — never refresh it.

## Default Flows

**New project:** `create → refine → initialize → plan → implement → test → review → deploy`

**Update/fix:** `update/fix → refine → initialize-branch → plan → implement → test → review → merge → deploy`

| Stage | Purpose |
|-------|---------|
| create | Create project folder, `requirements.md`, and top-level stubs |
| refine | Resolve ambiguities only; keep original meaning |
| initialize | Init git repo (new project) or create a new branch (update/fix) |
| plan | Archive old `plan.md`; write new plan |
| implement | Write code; update `implementation.md` |
| test | Test → fix → retest until all requirements pass |
| review | Review for cleanliness/correctness; fix all issues found |
| merge | Merge branch to main; update `CHANGELOG.md` and living docs |
| deploy | Deploy; update `deployment.md` and `README.md` |

## agent-workflow Context

When invoked inside an `agent-workflow`, call the `agent-workflow` skill's **continue-workflow** action immediately after each stage completes.

## Stage Dispatch

| Intent | Reference |
|--------|-----------|
| Start a new project | `references/create.md` |
| Clarify requirements | `references/refine.md` |
| Brainstorm ideas | `references/brainstorm.md` |
| Apply brainstorm to requirements | `references/apply-brainstorm.md` |
| Initialize repo or branch | `references/initial.md` |
| Create a dev plan | `references/plan.md` |
| Implement from plan | `references/implement.md` |
| Review for defects | `references/review.md` |
| Test the implementation | `references/test.md` |
| Deploy the project | `references/deploy.md` |
| Apply `update.md` changes | `references/update.md` |
| Fix issues from `issues.md` | `references/fix-issues.md` |
| Merge update/fix branch | `references/merge.md` |

If the intent matches multiple stages, ask before acting.

## Instructions

1. **Identify the project** — confirm `workspace/vibe-coding/{project-name}/`; if new, dispatch to `create`.
2. **Identify the stage** — map the request to one dispatch entry; announce role(s) and stage.
3. **Read the reference** — follow `references/{stage}.md`.
4. **Apply lifecycle rules** — archive intermediates, refresh living docs, never rewrite `initialized.md`.
5. **Report** — state what ran, which files changed, and what comes next.

## Key Principles

- **Single source of truth**: living docs always reflect current state.
- **Archive before overwrite**: never lose intermediate content.
- **Boundary discipline**: stay in the project folder.
- **One stage per turn**: run multiple stages in sequence if asked.
- **Refresh after change**: always update living docs before reporting done.
