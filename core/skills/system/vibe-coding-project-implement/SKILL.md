---
name: vibe-coding-project-implement
description: Implement a Vibe Coding project based on its plan.md file. Use when a project has an approved plan and should move into code changes.
---

# AI Builder - Vibe Coding Project Implement

Implement the project according to its `plan.md`.

## When to Use This Skill

- The user wants code written from `plan.md`
- The plan is approved and implementation should start
- The project is moving from planning into execution

## Your Roles in This Skill

- **Backend Developer**: Make the code changes
- **Project Manager**: Keep implementation aligned with the plan

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Plan

Read the referenced `plan.md` and identify the implementation steps in order.

### Step 2: Implement the Plan

Make the required code changes. If a meaningful deviation is necessary, explain it before proceeding.

### Step 3: Verify the Changes

Run the most relevant tests or static checks that fit the changed code.

### Step 4: Summarize the Result

Report what was implemented, what was verified, and any remaining risks.
