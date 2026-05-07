# Stage Reference: initial

Initialize the project repo and first setup based on `requirements.md`.

## When to Use

- The user wants to initialize a new coding project from `requirements.md`
- First-pass repo setup is needed
- GitHub initialization may be part of bootstrap

## Steps

### Step 1: Review the Requirement

Read `design-docs/requirements.md` and identify likely stack, deliverables, and initialization needs.

### Step 2: Prepare the Local Project

Create or confirm the local project structure needed for implementation.

### Step 3: Initialize Version Control

Ask the user how they want to manage code with git. Default: use the Skill Pilot root project repository (no separate repo).

- **If the user provides an existing git URL**: clone and merge into the project folder, then add as a git submodule of the root project.
- **If the user asks to create a new GitHub repo**: use the `agent-browser` skill to create the repo on GitHub, then add it as a git submodule of the root project.
- **Otherwise (default)**: the project lives inside the root Skill Pilot repository with no separate git setup.

### Step 4: Record the Initial State

Write `design-docs/initialized.md` as a write-once mark capturing:

- Project name and path
- Chosen git strategy and remote (if any)
- Top-level directories created
- Date of initialization

`initialized.md` is a living doc only in the sense that it stays in `design-docs/`. Do NOT refresh or rewrite it on later stages — it is a one-shot record that the initialization step has finished.

### Step 5: Report

Confirm what was initialized and that `initialized.md` was written.
