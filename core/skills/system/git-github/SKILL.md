---
name: git-github
description: Handle Git and GitHub work including commits, conventional commit message drafting, partial file or folder merges, and squash merges. Use when the user asks to commit, draft a commit message, merge branches, selectively merge paths, squash merge, push, or coordinate GitHub-oriented source control tasks.
metadata:
  short-description: Manage Git/GitHub commits and merges.
---

# AI Builder - Git and GitHub

Manage Git and GitHub source-control tasks with clean history, explicit scope, and verification.

## When to Use This Skill

- User asks to commit, commit changes, save changes to git, or draft a commit message.
- User asks for a conventional commit message based on local changes.
- User asks to merge a branch, squash merge, or selectively merge specific files or folders.
- User asks for Git/GitHub source-control work where branch state, staged changes, or history cleanliness matters.

## Your Roles in This Skill

- **DevOps Engineer**: Inspect repository state, prepare safe Git operations, and verify the result.
- **Project Manager**: Clarify scope, approval points, and whether changes should be committed or pushed.
- **Technical Writer**: Draft concise conventional commit messages and merge summaries.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Identify the Git task

- For commit-message drafting or commit requests, use `references/commit-message.md`.
- For partial file/folder merges or squash merges, use `references/merge.md`.
- For other Git/GitHub work, inspect branch and working-tree state first, then choose the smallest safe operation that satisfies the user request.

### Step 2: Check repository state

Before changing Git state, inspect the current branch, working tree, staged changes, and relevant remote/branch information. Preserve unrelated user changes.

### Step 3: Confirm approval-sensitive actions

Ask before committing, pushing, deleting branches, rewriting history, or making broad merge changes unless the user explicitly authorized that action.

### Step 4: Execute and verify

Run the selected Git operation, inspect the resulting status or diff, and report the outcome with the files or commits affected.

## Expected Output

- A clear commit message draft, completed commit, merge result, or Git/GitHub operation summary.
- Verification result, including current branch/status and any follow-up action needed.
