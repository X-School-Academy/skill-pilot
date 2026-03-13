---
name: skill-pilot-feature-update
description: Update a Skill Pilot feature based on update.md. Use when an existing feature needs additional changes.
---

# AI Builder - Skill Pilot Feature Update

Apply a feature update from `update.md`.

## When to Use This Skill

- The feature already exists
- The requested work is described in `update.md`

## Your Roles in This Skill

- **Backend Developer**: Apply the update
- **Project Manager**: Keep the changes aligned with the request

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Read the update request

Read the referenced `update.md`.

### Step 2: Implement the requested change

Make the update and verify it.
