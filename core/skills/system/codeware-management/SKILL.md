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
- The user wants to replace the sample `workspace/` submodule with a new private GitHub repo of their own

## Your Roles in This Skill

- **DevOps Engineer**: Manage remotes, branch state, fetch, merge, reset, push, and recovery steps safely
- **Backend Developer (Engineer)**: Resolve merge conflicts and repair code issues after sync or restore
- **Release Engineer**: Walk pending entries in `about/changelog/`, apply upgrade notices in order, and keep `about/version.json5` and `workspace/config/version.json5` consistent with applied state
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
- `create private workspace repo`: guide the user through replacing the sample `workspace/` submodule with a new empty private GitHub repo of their own, following `workspace/README.md`

Always use the official repo URL as the upstream source:

- `https://github.com/X-School-Academy/skill-pilot.git`

### Step 2: Check repo safety before changing Git state

Before any branch or remote operation:

- Confirm the current branch, status, and remotes
- Check for uncommitted changes
- If the requested operation is destructive, require explicit user approval before continuing
- For `update` and `restore`, also record the pre-operation applied state: `about/version.json5` → `{ version, build }` and `workspace/config/version.json5` → `{ version }`. These are needed to walk pending upgrade notices correctly, and the restore flow depends on them to avoid skipping migrations.

For concrete Git command sequences and decision rules, refer to `references/git-workflows.md`.

### Step 3: Run the selected flow

- For `update` or `restore`, follow `references/git-workflows.md`
- For `add remote` or `contribute`, use `references/github-contribution.md`
- For `create private workspace repo`, follow `references/private-workspace-setup.md`, which mirrors the steps documented in `workspace/README.md`

### Step 3.5: Apply pending upgrade notices (update and restore only)

After the Git state has advanced but before reporting success:

- Read `about/AGENTS.md` and follow its **Upgrade procedure** (for `update`) or **Restore procedure** (for `restore`).
- Walk every pending `## Build <n>` section in `about/changelog/*.md` in ascending `(version, build)` order.
- Apply each build's `### Upgrade notices` in order, including any `workspace/*` migrations.
- After each build's steps succeed, update `about/version.json5` to that build's `(version, build)`. If the build's `### Workspace target` differs from the current `workspace/config/version.json5`, update that file too as instructed by the notices.
- If any step fails, stop before bumping `about/version.json5` past the failing build and surface the failure.

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
- Applied Skill Pilot version and build before and after, and workspace version before and after (for `update` and `restore`)
- List of changelog builds whose upgrade notices were applied, if any
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
- `about/version.json5` tracks the *applied* state of a checkout; it is bumped by the upgrade procedure, not by release commits. Never write a future `(version, build)` into it before the corresponding notices have been applied.
- Skill Pilot agent version and workspace version move independently. Only bump `workspace/config/version.json5` when a changelog build explicitly states a new `Workspace target`.
