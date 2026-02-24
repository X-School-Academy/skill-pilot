---
name: system-development
description: Manage system development tasks under core/development/ with structured workflows for new tasks (requirement, plan, implement, summary) and reviews/updates. Use when creating, implementing, or reviewing system development tasks.
---

# AI Builder - System Development

This skill manages structured development tasks under `core/development/`. It supports two workflows: creating new tasks with approval gates at each stage, and reviewing or updating existing tasks.

## When to Use This Skill

- User asks to create a new development task or feature
- User provides a requirement file and asks to plan, implement, or summarize
- User wants to implement a task that lives under `core/development/`
- User asks to review or update an existing development task
- User wants to resume an incomplete development task

## Your Roles in This Skill

- **Project Manager**: Coordinate the workflow, enforce approval gates, manage the task folder and file structure.
- **Backend Developer**: Implement code changes based on the approved dev plan.
- **Technical Writer**: Write and maintain `requirement.md`, `dev-plan.md`, `dev-summary.md`, and `README.md`.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Determine which workflow applies, then follow its steps.

### Workflow A: New Task

Use when the user wants to create or resume a development task.

#### Step 1: Create the Task Folder

As a **Project Manager**, create `core/development/{task-name}/` using a short, descriptive, kebab-case name.

If the folder already exists and files are present, this is a **resumed task** — read all existing files, check the requirement file for grammar issues, present it for re-approval, then skip to whichever step the task left off at.

#### Step 2: Requirement

As a **Technical Writer**, capture the user's original request in a requirement file (e.g., `requirement.md` or a user-provided file like `{task-name}.md`). Apply grammar and clarity fixes only — do NOT add planning details, implementation steps, or agent commentary. This file is the user's voice.

If the user has already provided a requirement file in the task folder, use it as-is (grammar fixes only).

**Ask the user to approve** the requirement before proceeding.

#### Step 3: Dev Plan

As a **Project Manager** and **Backend Developer**, write a dev plan file (e.g., `dev-plan.md` or `{task-name}-dev-plan.md`) containing:
- Code review and gap analysis of the current codebase against the requirement
- Numbered implementation steps with specific file paths and changes
- Open questions for the user (if any design decisions need clarification)

**Ask the user to approve** the dev plan before proceeding. Record confirmed design decisions in the plan.

#### Step 4: Implement the Plan

As a **Backend Developer**, implement the approved plan step by step. Follow the plan exactly — if deviations are needed, explain why and get approval first.

#### Step 5: Summary

As a **Technical Writer**, write a summary file (e.g., `dev-summary.md` or `{task-name}-summary.md`) documenting:
- What was done (organized by step or component)
- Files changed with descriptions
- Design decisions confirmed during planning

#### Step 6: Update the Requirement File

As a **Technical Writer**, update the original requirement file to reflect any design decisions made during the planning phase (e.g., choosing to keep existing APIs instead of creating new ones, confirmed behaviors). Apply grammar fixes. Keep the file as close to the original as possible — only update what changed as a result of the discussion.

#### Step 7: Write `README.md`

As a **Technical Writer**, create or update `README.md` as a quick-index file. Keep it simple:
- A short heading describing the task
- **Features**: Flat bullet list of what was built (one line per feature)
- **Docs** table: File | Contents (listing all docs in the task folder)

Do NOT add verbose Goal paragraphs or separate Files tables — keep it scannable.

### Workflow B: Review / Update

Use when the user wants to review or modify an existing development task.

#### Step 1: Locate the Task

As a **Project Manager**, find the task folder under `core/development/`. If the user gives a partial name, list available folders and confirm.

#### Step 2: Read Current State

Read `README.md` first for an overview, then read other files as needed (`requirement.md`, `dev-plan.md`, `dev-summary.md`).

#### Step 3: Perform the Review or Update

As the appropriate role(s), carry out the requested review or update. Get user approval before making significant changes.

#### Step 4: Update Documentation

As a **Technical Writer**, update all affected docs:
- `requirement.md` — only if the requirement itself changed
- `dev-plan.md` — if the approach changed
- `dev-summary.md` — append new changes under a new section
- `README.md` — update to reflect current state

## Scope

- **Primary codebase**: `core/engine/` (Python + uv) — most implementation work happens here
- **Also in scope**: `core/webui/` (Next.js + pnpm), `core/skills/system/`, `dev-swarm/skills/`
- **Out of scope** (ignore unless directly related to dev-swarm system):
  - `NN-*` stage folders (e.g., `00-init-ideas/`, `05-prd/`)
  - `courses/`
  - `features/`
  - `src/`

When planning and implementing, focus on `core/engine/` first. Do not read, modify, or reference out-of-scope directories unless the task explicitly involves the dev-swarm system.

## Key Principles

- **The requirement file is the user's voice** — grammar fixes only, no agent additions; update it after planning only to reflect confirmed design decisions
- **Every major step requires approval** — never skip an approval gate
- **Resume from current state** — if files exist, pick up where the workflow left off
- **All implementation details go in the dev plan** — not in the requirement file
- **Verify your work** — run builds/tests before writing the summary
- **Stay in scope** — only touch directories listed under Scope above
- **Flexible file naming** — files can use `requirement.md` / `dev-plan.md` / `dev-summary.md` or `{task-name}.md` / `{task-name}-dev-plan.md` / `{task-name}-summary.md` patterns
