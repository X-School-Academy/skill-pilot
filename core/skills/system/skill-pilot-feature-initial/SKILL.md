---
name: skill-pilot-feature-initial
description: Initialize Skill Pilot feature work by creating a new branch for the feature based on its requirement file. Use when a new feature is ready to move into implementation setup.
---

# AI Builder - Skill Pilot Feature Initial

Prepare a feature branch for a new Skill Pilot feature.

## When to Use This Skill

- A feature requirement exists
- A new branch should be created before planning or implementation

## Your Roles in This Skill

- **Project Manager**: Coordinate the setup step
- **Backend Developer**: Prepare the branch naming and initial structure

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Read the requirement

Read the referenced `requirements.md`.

### Step 2: Verify branch readiness

Before creating a new branch, confirm the working tree is on the user branch with no uncommitted changes:

- If not on the user branch, switch to the user branch first.
- If there are uncommitted changes, ask the user whether to commit them or stash them before proceeding.

### Step 3: Create and switch to the feature branch

Detect the trigger context and create the appropriate branch from the user branch:

- **New feature** (driven by `requirements.md`): create `feature/{feature-name}`
- **Update** (driven by `update.md`): create `update/{feature-name}`
- **Bug fix** (driven by `issues.md`): create `fix/{feature-name}`

Switch to the new branch and continue working on it.
