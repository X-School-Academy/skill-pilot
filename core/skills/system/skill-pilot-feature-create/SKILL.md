---
name: skill-pilot-feature-create
description: Create a new Skill Pilot feature requirement under core/development/{feature}/requirements.md. Use when a user wants to start feature development from a requirement prompt.
---

# AI Builder - Skill Pilot Feature Create

Create a new feature development requirement in `core/development/`.

## When to Use This Skill

- The user wants a new feature started
- The feature needs a `requirements.md`

## Your Roles in This Skill

- **Project Manager**: Create the feature folder structure
- **Technical Writer**: Write the initial requirement file

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Determine the feature name

Choose a short kebab-case feature folder name.

### Step 2: Create the requirement

Write `core/development/{feature-name}/requirements.md` from the user's request.
