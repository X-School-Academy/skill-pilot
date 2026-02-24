# General Development Stage Rules

## Role Selection

Based on the stage context and project details, pick the best roles from `dev-swarm/docs/dev-swarm-roles.md`.

## Role Communication

Announce your actions before performing them:

**As a {Role} [and {Role}, ...], I will {action description}**

## Stage Completion Rules

1. If the stage folder already has files and no uncommitted changes: tell the user the stage is complete and ask if they want updates.
2. If the stage folder has files with uncommitted changes: refine existing files based on those changes.
3. After each step/stage: ask the user if they want to commit and push to remote, then follow their instruction.
4. If the user asks to skip: create a `SKIP.md` file in that stage folder with the reason for skipping.

## Stage Documentation Requirements

### Minimum Requirements

Every stage folder must contain at least one of the following:

1. **`README.md`** - The stage proposal and summary document (required for active stages)
2. **`SKIP.md`** - Skip reason document (only if stage is intentionally skipped)

**00-init-ideas, 05-prd, 08-tech-specs, and 10-sprints are non-skippable stages**

### Writing Guidelines

- Avoid using Markdown tables in any files
- Keep docs small and simple
- Avoid over-documentation
- Write for experts, not beginners
- No code snippets - guidelines and key info only

## Prior Stage Reference Policy

- When starting a new stage, do not re-read prior-stage files that were already reviewed in earlier stages unless the user indicates they changed.
- If the user says prior-stage files were updated, re-read only the updated files and note the refresh.

## Create Stage Proposal Rules

1. Assess project complexity before selecting files
2. Select only files that provide value for this project
3. Justify each file selection
4. Present proposal to user before execution
