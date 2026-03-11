---
name: vibe-coding-project-fix-issues
description: Fix project issues defined in issues.md for a Vibe Coding project. Use when the user wants bug reports or issue lists turned into concrete fixes.
---

# AI Builder - Vibe Coding Project Fix Issues

Fix issues for a Vibe Coding project based on `issues.md`.

## When to Use This Skill

- The user wants issues fixed from `issues.md`
- The project has bug reports or issue notes collected already
- The work is bug fixing rather than feature planning

## Your Roles in This Skill

- **Backend Developer**: Implement the fixes
- **QA Engineer**: Validate the fixes against the reported issues

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Issue File

Read the referenced `issues.md` and inspect the affected code.

### Step 2: Fix the Issues

Implement targeted fixes for the reported problems.

### Step 3: Verify the Fixes

Run the most relevant checks to confirm the issues are resolved.

### Step 4: Sync Stage Files

1. Update `requirements.md`, `plan.md`, and `implement.md` to reflect any changes made by the fixes.
2. If the fixes were driven by `issues.md`, create `issues-plan.md` and `issues-impl.md` as the plan and implementation records specific to this fix cycle.
3. Note: `issues.md`, `issues-plan.md`, and `issues-impl.md` are temporary files that the user may remove after review.

### Step 5: Summarize the Result

Report which issues were fixed, how they were verified, and any remaining follow-up items.
