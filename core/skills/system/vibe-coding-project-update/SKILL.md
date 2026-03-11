---
name: vibe-coding-project-update
description: Update a Vibe Coding project based on update.md. Use when the user wants the existing project changed according to a written update request.
---

# AI Builder - Vibe Coding Project Update

Update an existing project based on its `update.md` request.

## When to Use This Skill

- The user wants changes applied from `update.md`
- The project already exists and needs iteration
- The task is an update rather than a net-new implementation

## Your Roles in This Skill

- **Backend Developer**: Apply the requested changes
- **Project Manager**: Keep the update aligned with the written request

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Update Request

Read the referenced `update.md` and inspect the relevant code paths.

### Step 2: Implement the Update

Apply the requested changes with minimal unrelated modifications.

### Step 3: Verify the Update

Run the most relevant targeted checks for the changed behavior.

### Step 4: Sync Stage Files

1. Update `requirements.md`, `plan.md`, and `implement.md` to reflect any changes made by this update.
2. If the update was driven by `update.md`, create `update-plan.md` and `update-impl.md` as the plan and implementation records specific to this update cycle.
3. Note: `update.md`, `update-plan.md`, and `update-impl.md` are temporary files that the user may remove after review.

### Step 5: Summarize What Changed

Report the updated behavior, verification, and any remaining risks.
