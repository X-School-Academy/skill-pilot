---
name: vibe-coding-project-plan
description: Create a development plan for a Vibe Coding project from its requirement file. Use when a project is ready to move from requirements into an implementation plan.
---

# AI Builder - Vibe Coding Project Plan

Create a concrete development plan from a Vibe Coding requirement file.

## When to Use This Skill

- The user wants a dev plan from `requirements.md`
- The project needs a file-by-file implementation approach
- The next step is implementation planning, not coding yet

## Your Roles in This Skill

- **Project Manager**: Define scope and phases
- **Backend Developer**: Identify real code changes

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Package Management Tools

Use `uv` for Python projects and `pnpm` for Node.js projects unless the user asks to use a different tool. Include this in the plan when relevant.

## Instructions

### Step 1: Read the Requirement

Read the referenced `requirements.md`.

### Step 2: Review the Current Codebase

Inspect the relevant code and identify the current implementation gaps.

### Step 3: Write the Plan

Create or update `plan.md` in the same project folder. Include scope, current-state analysis, implementation phases, likely file changes, and any open questions.

### Step 4: Ask for Approval

Present the plan as ready for approval before implementation starts.
