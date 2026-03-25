---
name: github-gh-cli
description: Use GitHub CLI for GitHub.com tasks such as authentication, repository operations, pull requests, issues, releases, workflow runs, and GitHub API calls. Trigger this skill when the user asks to use GitHub gh CLI or wants GitHub work done through the terminal.
---

# AI Builder - GitHub GH CLI

Use GitHub CLI as the default execution path for GitHub.com work in the terminal.

## When to Use This Skill

- The user explicitly asks to use GitHub `gh` CLI
- The task involves GitHub repositories, pull requests, issues, releases, actions, or notifications from the terminal
- The task requires GitHub API access and `gh api` is an appropriate interface
- `gh` is missing or not authenticated and the user wants GitHub CLI enabled first

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Execute `gh` commands and structure API queries for the requested GitHub task
- **SysOps Engineer**: Install `gh`, manage local CLI configuration, and run the interactive auth flow safely
- **Security Engineer**: Warn before opening external sites and keep authentication/account actions deliberate
- **Technical Writer**: Summarize the commands run, results, and any follow-up needed

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Check whether `gh` is installed

Run `command -v gh`.

- If `gh` exists, continue to Step 2
- If `gh` is missing, install it with `brew install gh`

### Step 2: Check authentication

Run `gh auth status`.

- If authenticated, continue to Step 3
- If not authenticated, refer to [references/install-and-auth.md](references/install-and-auth.md) and complete the login flow there

### Step 3: Use `gh` for the requested task

Refer to [references/usage-patterns.md](references/usage-patterns.md) and choose the smallest correct `gh` or `gh api` command path for the user's task.

## Expected Output

- `gh` available locally
- Authenticated GitHub CLI when needed
- Requested GitHub task completed through `gh` or `gh api`

## Key Principles

- Prefer `gh` over browser-heavy GitHub workflows when terminal execution is sufficient
- Keep the main skill small and route operational detail to references
- Use `gh api` deliberately rather than as a vague fallback
