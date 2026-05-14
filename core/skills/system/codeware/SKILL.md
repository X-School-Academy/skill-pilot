---
name: codeware
description: Manage Skill Pilot codeware operations and feature lifecycle work. Use when the user wants to sync or restore codeware, configure a personal fork, contribute upstream, create a private workspace repo, or run feature development steps such as create, refine, initial, plan, implement, review, test, merge, freeze, update, or fix issues.
---

# AI Builder - Codeware

Handle Skill Pilot codeware maintenance and feature development workflows.

## When to Use This Skill

- The user wants to update, restore, repair, or contribute Skill Pilot codeware
- The user wants to configure remotes, forks, contribution branches, or a private workspace repo
- The user wants to create, refine, plan, implement, review, test, merge, freeze, update, or fix a feature under `core/development/`

## Your Roles in This Skill

- **Project Manager**: Identify the requested operation, keep scope clear, and coordinate approvals
- **Backend Developer**: Implement code changes, resolve conflicts, and repair issues
- **DevOps Engineer**: Manage branches, remotes, fetch, merge, reset, push, and workspace repo setup
- **Release Engineer**: Apply pending upgrade notices and maintain version state
- **QA Engineer**: Verify changes with targeted tests and integration checks
- **Technical Writer**: Keep requirements, plans, reports, and workflow outputs clear
- **Security Engineer**: Warn about remote website prompt-injection risk before browser automation

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Identify the operation

Map the user request to one operation family:

- Codeware maintenance: `update`, `restore`, `add remote`, `contribute`, or `create private workspace repo`
- Feature lifecycle: `create`, `refine`, `initial`, `plan`, `implement`, `review`, `test`, `merge`, `freeze`, `update feature`, or `fix issues`

### Step 2: Load the correct reference

- For codeware `update` or `restore`, use `references/git-workflows.md`
- For `add remote` or `contribute`, use `references/github-contribution.md`
- For `create private workspace repo`, use `references/private-workspace-setup.md`
- For feature lifecycle work, use `references/feature-lifecycle.md`
- If running inside an `agent-workflow`, also load `references/feature-lifecycle-agent-workflow.md`

### Step 3: Execute with safety checks

- Inspect current state before changing files, branches, remotes, or version markers
- Ask for confirmation before destructive Git operations or remote browser automation
- Preserve user work unless an explicitly approved restore flow requires otherwise
- Keep temporary or intermediate files under `.skillpilot/temp/` when needed

### Step 4: Verify and report

Run targeted verification for the affected area and report:

- Operation performed
- Files, branches, remotes, or feature documents changed
- Tests or checks run
- Blockers, unresolved risks, or manual follow-up

## Expected Output

- A completed codeware maintenance action, or
- A completed feature lifecycle step under `core/development/`, or
- A clear blocker report with the current repo state and next decision needed
