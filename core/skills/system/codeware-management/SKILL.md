---
name: codeware-management
description: Manage the codeware branching workflow for update sync, restore-from-codeware recovery, personal fork remote setup, and contribution pull requests. Use when the user wants to sync official updates, recover a broken user branch, connect a personal Git remote, or contribute changes back upstream.
---

# AI Builder - Codeware Management

Handle the official Skill Pilot branch workflow around `codeware`, `user`, personal fork remotes, and clean contribution branches.

## When to Use This Skill

- The user wants to update their `user` branch from the official `codeware` branch
- The user wants to restore a broken `user` branch from the official repo
- The user wants to add or fix their personal Git remote for backup or contribution
- The user wants to create a clean contribution branch and open a pull request

## Your Roles in This Skill

- **DevOps Engineer**: Manage remotes, branch state, fetch, merge, reset, push, and recovery steps safely
- **Backend Developer (Engineer)**: Resolve merge conflicts and repair code issues after sync or restore
- **Technical Writer**: Keep the workflow explicit, auditable, and aligned with `CONTRIBUTING.md`
- **Security Engineer**: Require trust confirmation before browser automation on remote websites and call out destructive Git risk

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Identify the requested operation

Map the request to one of these operations:

- `update`: merge the latest official `upstream/codeware` into the local `user` branch
- `restore`: back up the current `user` branch, then force realign it to `upstream/codeware` before fixing remaining errors
- `add remote`: connect the user's fork as `origin`, using a provided Git URL or browser-assisted fork flow
- `contribute`: create a clean feature branch from `upstream/contrib`, push it to the user's fork, and open a pull request

Always use the official repo URL as the upstream source:

- `https://github.com/X-School-Academy/skill-pilot.git`

### Step 2: Check repo safety before changing Git state

Before any branch or remote operation:

- Confirm the current branch, status, and remotes
- Check for uncommitted changes
- If the requested operation is destructive, require explicit user approval before continuing

For concrete Git command sequences and decision rules, refer to `references/git-workflows.md`.

### Step 3: Run the selected flow

- For `update` or `restore`, follow `references/git-workflows.md`
- For `add remote` or `contribute`, use `references/github-contribution.md`

### Step 4: Resolve resulting issues

After merge, reset, cherry-pick, or branch creation:

- Fix merge conflicts carefully without discarding user work unless the approved restore flow requires it
- Run targeted verification for the affected area
- If the requested recovery still cannot be completed safely, stop and explain the blocker clearly

### Step 5: Report the result

Return:

- Operation performed
- Current branch and any new branch names
- Remote configuration outcome
- Conflict or recovery actions taken
- Verification status and remaining manual follow-up, if any

## Expected Output

- A safely updated or restored `user` branch, or
- A correct `origin`/`upstream` remote setup, or
- A pushed contribution branch with a pull request opened against `X-School-Academy/skill-pilot:contrib`

## Key Principles

- Treat `upstream` as the official repository and `origin` as the user's personal fork
- Keep daily work on `user`
- Only create contribution branches when the user is actually contributing
- Require explicit confirmation before destructive restore actions
- Before opening GitHub in a browser tool, warn about prompt injection risk and confirm `github.com` is trusted
