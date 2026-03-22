---
name: vibe-coding-project-initial
description: Initialize a Vibe Coding project for delivery by preparing the repository and first project setup based on the requirement file. Use when a project should move from requirements into initial repo setup, including GitHub initialization when appropriate.
---

# AI Builder - Vibe Coding Project Initial

Initialize a Vibe Coding project from its requirement file and prepare the first repository setup.

## When to Use This Skill

- The user wants to initialize a new coding project from `requirements.md`
- The project needs first-pass repo setup
- GitHub initialization is part of the requested project bootstrap

## Your Roles in This Skill

- **Project Manager**: Confirm initialization scope and sequencing
- **Backend Developer**: Prepare the project structure
- **DevOps Engineer**: Handle repository initialization steps

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Review the Requirement

Read the referenced `requirements.md` and identify the likely stack, deliverables, and initialization needs.

### Step 2: Prepare the Local Project

Create or confirm the local project structure needed for implementation.

### Step 3: Initialize Version Control

Ask the user how they want to manage the project's code with git. The default is to use the Skill Pilot root project repository (no separate repo).

**If the user provides an existing git URL:**
- Clone and merge the repo into the project folder.
- Set it up as a git submodule of the root project.

**If the user asks to create a new GitHub repo:**
- Use web browser agent skill to create the repo from the GitHub website.
- Then add it as a git submodule of the root project.

**Otherwise (default):**
- The project lives inside the root Skill Pilot repository with no separate git setup needed.

### Step 4: Record the Initial State

Create or update project docs so the initialized state is clear for later planning and implementation.
