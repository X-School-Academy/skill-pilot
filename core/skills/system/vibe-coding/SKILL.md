---
name: vibe-coding
description: Manage the full lifecycle of a Vibe Coding project — create, refine, brainstorm, initialize, plan, implement, review, test, deploy, update, and fix issues. Use when the user wants to start a new project from a prompt, evolve its requirements, plan or write code, validate or deploy it, or apply updates and bug fixes against an existing project.
---

# AI Builder - Vibe Coding Project Lifecycle

This skill drives every stage of a Vibe Coding project. Each stage has a focused reference file under `references/`. This `SKILL.md` defines the project layout, the file lifecycle rules, and how to dispatch to the right reference based on the current task.

## When to Use This Skill

- The user wants to start, evolve, build, validate, deploy, or update a Vibe Coding project
- The project lives (or will live) at `workspace/vibe-coding/{project-name}/`
- The user names a stage (create, refine, brainstorm, plan, implement, review, test, deploy, update, fix) or describes the intent in their own words
- The user asks to apply `issues.md`, `update.md`, or `brainstorm.md` to the project

## Your Roles in This Skill

- **Project Manager**: Choose the right stage, keep the project state coherent, and enforce the file-lifecycle rules
- **Technical Writer**: Maintain clear, current design docs in `design-docs/`
- **Backend Developer**: Make code changes during implement, update, and fix stages
- **DevOps Engineer**: Handle initialization and deployment
- **Code Reviewer**: Drive review-stage findings
- **QA Engineer**: Drive test-stage validation
- **Creative Strategist**: Drive brainstorming

(Apply only the roles relevant to the chosen stage.)

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Project Layout

Every project uses this structure:

```
workspace/vibe-coding/{project-name}/
├── design-docs/
│   ├── requirements.md       # living - latest scope and intent
│   ├── plan.md               # living - latest implementation plan
│   ├── implement.md          # living - latest implementation summary
│   ├── deployment.md         # living - latest deployment record
│   ├── initialized.md        # write-once mark that init step completed
│   └── archive/              # snapshots of intermediate / review-output files
│       ├── brainstorm.{timestamp}.md
│       ├── issues.{timestamp}.md
│       ├── update.{timestamp}.md
│       ├── reviewed.{timestamp}.md
│       ├── tested.{timestamp}.md
│       ├── issues-plan.{timestamp}.md
│       ├── issues-impl.{timestamp}.md
│       ├── update-plan.{timestamp}.md
│       └── update-impl.{timestamp}.md
└── (project source code, if it lives in-tree)
```

The `create` stage is responsible for creating `design-docs/` and `design-docs/archive/` when the project is first bootstrapped.

## File Lifecycle Rules

**Living design docs** — kept in `design-docs/`, overwritten in place, latest version always wins:

- `requirements.md`
- `plan.md`
- `implement.md`
- `deployment.md`
- `initialized.md` (write-once mark; do not refresh after initialization)

After every stage that meaningfully changes scope, plan, or code, refresh `requirements.md`, `plan.md`, and `implement.md` so the latest design state is always available for reference.

**Human-loop intermediates** — produced for human review or as the user's instruction. After they have been consumed by the next stage, move them to `design-docs/archive/` with a timestamp suffix:

- `brainstorm.md` (consumed by `apply-brainstorm`)
- `issues.md` (consumed by `fix-issues`)
- `update.md` (consumed by `update`)
- `reviewed.md` (output of `review`, consumed when issues/updates are derived from it)
- `tested.md` (output of `test`, consumed when issues/updates are derived from it)

**Review-output intermediates** — created during fix or update cycles for human review, then archived:

- `issues-plan.md`, `issues-impl.md` (created by `fix-issues`)
- `update-plan.md`, `update-impl.md` (created by `update`)

**Archive naming convention** — always `{basename}.{YYYY-MM-DD-HHMM}.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/issues.md "design-docs/archive/issues.$timestamp.md"
```

Apply the same pattern to renamed-and-archived files (e.g., `update-plan.md` → `design-docs/archive/update-plan.$timestamp.md`).

## Lifecycle Loop

Typical flow once a project exists:

1. `review` or `test` → produces `reviewed.md` / `tested.md`
2. User authors `issues.md` (bugs) or `update.md` (change request) based on the reviewed/tested output
3. `fix-issues` or `update` → produces `issues-plan.md` + `issues-impl.md` (or `update-plan.md` + `update-impl.md`) for human review, applies the change, refreshes the living design docs, and archives the intermediates with timestamps

## Stage Dispatch

Pick the matching reference file based on the user's intent:

- If the user wants to **start a new project from a prompt**, refer to `references/create.md`
- If the user wants to **clean up `requirements.md` for clarity**, refer to `references/refine.md`
- If the user wants to **brainstorm ideas/alternatives** for an existing requirement, refer to `references/brainstorm.md`
- If the user wants to **merge brainstorm.md into requirements.md**, refer to `references/apply-brainstorm.md`
- If the user wants to **initialize the project repo / first setup**, refer to `references/initial.md`
- If the user wants a **development plan from `requirements.md`**, refer to `references/plan.md`
- If the user wants to **implement code from `plan.md`**, refer to `references/implement.md`
- If the user wants to **review the implementation for defects**, refer to `references/review.md`
- If the user wants to **test the implementation**, refer to `references/test.md`
- If the user wants to **deploy the project**, refer to `references/deploy.md`
- If the user wants to **apply changes from `update.md`**, refer to `references/update.md`
- If the user wants to **fix issues from `issues.md`**, refer to `references/fix-issues.md`

If the user's intent matches multiple stages, ask which one to run rather than guessing.

## Instructions

### Step 1: Identify the Project

Confirm the target `workspace/vibe-coding/{project-name}/` folder. If the project does not exist yet and the user is starting fresh, dispatch to `references/create.md`.

### Step 2: Identify the Stage

Map the user's request to one stage in the dispatch list above. Announce the role(s) and the chosen stage before acting.

### Step 3: Read the Stage Reference

Read the matching `references/{stage}.md` file and follow its steps.

### Step 4: Apply Lifecycle Rules

While executing the stage, honor the file-lifecycle rules:

- Write outputs to `design-docs/` (living) or keep them at the conventional path until the next stage archives them
- After consuming a human-loop intermediate, archive it with the timestamp pattern
- After consuming a review-output intermediate (`issues-plan.md`, `issues-impl.md`, `update-plan.md`, `update-impl.md`), move it to `design-docs/archive/` with the timestamp pattern
- After meaningful changes, refresh `requirements.md`, `plan.md`, and `implement.md` so the living design docs reflect the current state
- Never refresh `initialized.md` after the initial step completes

### Step 5: Report

Summarize what stage ran, which files were updated or archived, and what the user should do next.

## Key Principles

- **Single source of truth**: living design docs in `design-docs/` always reflect the latest project state
- **Archive before overwrite**: never lose human-loop or review-output content; archive with `{basename}.{YYYY-MM-DD-HHMM}.md`
- **Boundary discipline**: stay inside `workspace/vibe-coding/{project-name}/` unless the user asks otherwise
- **Stage-focused**: one stage per invocation; if the user asks for several, run them in sequence and announce each
- **Refresh after change**: any stage that changes code or scope must refresh the living design docs before reporting done
