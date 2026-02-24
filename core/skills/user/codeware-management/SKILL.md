---
name: codeware-management
description: Manage the codeware branching workflow for update sync, contribution PR flow, and restore from codeware baseline. Use when coordinating codeware, contrib, and user branches with conflict fixes and squash-only contrib integration.
---

# AI Builder - Codeware Management

This skill standardizes how to keep `codeware`, `contrib`, and `user` aligned, how to contribute features safely, and how to restore `user` to a known good codeware state.

## When to Use This Skill

- You need to sync updates from `codeware` into `contrib` and `user`
- You need to contribute features and open pull requests
- You need to resolve merge conflicts across the three branches
- You need to restore `user` branch behavior to match `codeware`

## Your Roles in This Skill

- **DevOps Engineer**: Execute branch operations, merge strategy, push flow, and PR sequence.
- **Backend Developer (Engineer)**: Resolve code-level conflicts and verify build/test health.
- **QA Engineer**: Validate that merged/restored branches are working before push or PR.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Preflight Safety Checks

1. Confirm working tree is clean: `git status --short`.
2. Confirm current branch and remotes: `git branch --show-current && git remote -v`.
3. Fetch latest refs before any merge: `git fetch --all --prune`.
4. Stop and ask user before destructive actions (`reset`, `rebase -i`, force push).

### Step 2: Update Workflow (Codeware-First Sync)

Goal: update from `codeware`, then merge into `contrib` and `user`, fixing conflicts.

- Follow `references/update.md`.

### Step 3: Contribute and Pull Request Workflow

Goal: update first, merge feature into `contrib` using squash-only strategy (no history), test, push, then create PR.

- Follow `references/contribute-pr.md`.

### Step 4: Restore Workflow

Goal: compare `user` against `codeware` and roll back problematic files/areas so `user` becomes a working copy.

- Follow `references/restore.md`.

### Step 5: Reporting

After each run, report:

1. Branches touched
2. Conflicts and how they were resolved
3. Test commands and results
4. Push status and PR links
5. Any skipped or blocked step

## Key Principles

- `codeware` is the stability baseline.
- Always run update sync before contribution PR flow.
- For `contrib`, use squash merge only; do not preserve feature branch history in `contrib`.
- Fix conflicts explicitly and retest before push.
- Keep rollback changes minimal and traceable.

## Expected Output

- Updated branches (`codeware`, `contrib`, `user`) per workflow
- Conflict resolutions committed to the correct branch
- Squash-only feature integration into `contrib`
- PR ready or created with test evidence
- Restored `user` branch when requested
