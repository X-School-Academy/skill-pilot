# Stage Reference: initial

Initialize the project repo and first setup based on `requirements.md`, or create a new git branch for an update or bug fix.

## When to Use

- **New project**: the user wants to initialize a new coding project from `requirements.md`; first-pass repo setup is needed.
- **Update or bug fix**: the user wants to start work on a change to an existing project; a new branch is needed for the work.

## New Project Path

### Step 1: Review the Requirement

Read `requirements.md` and identify likely stack, deliverables, and initialization needs.

### Step 2: Prepare the Local Project

Create or confirm the local project structure needed for implementation.

### Step 3: Initialize Version Control

Ask the user how they want to manage code with git. Default: use the Skill Pilot root project repository (no separate repo).

- **If the user provides an existing git URL**: clone and merge into the project folder, then add as a git submodule of the root project.
- **If the user asks to create a new GitHub repo**: use the `agent-browser` skill to create the repo on GitHub, then add it as a git submodule of the root project.
- **Otherwise (default)**: the project lives inside the root Skill Pilot repository with no separate git setup.

### Step 4: Record the Initial State

Write `initialized.md` as a write-once mark capturing:

- Project name and path
- Chosen git strategy and remote (if any)
- Top-level directories created
- Date of initialization

`initialized.md` stays in the project root. Do NOT refresh or rewrite it on later stages — it is a one-shot record that the initialization step has finished.

### Step 5: Report

Confirm what was initialized and that `initialized.md` was written.

## Update or Bug Fix Path

### Step 1: Derive the Branch Name

Derive a concise kebab-case branch name from the update or fix description (e.g., `fix-login-timeout`, `update-dark-mode`).

### Step 2: Create and Check Out the Branch

```bash
git checkout -b {branch-name}
```

### Step 3: Record the Branch

Append a note to `initialized.md` (it already exists) recording:

- Branch name
- Date created
- Brief description of the change

### Step 4: Report

Confirm the branch name and that the working tree is on the new branch.
