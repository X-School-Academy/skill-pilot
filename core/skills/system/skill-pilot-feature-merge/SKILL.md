---
name: skill-pilot-feature-merge
description: Merge a Skill Pilot feature and switch code back to the user branch to finish development. Use when implementation and validation are complete.
---

# AI Builder - Skill Pilot Feature Merge

Merge a completed feature and return the codebase to the user branch.

## When to Use This Skill

- The feature is complete
- Review and testing are done
- The work should be merged and finalized

## Your Roles in This Skill

- **Project Manager**: Confirm readiness to merge
- **Backend Developer**: Perform the merge and branch switch

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Confirm readiness

Read the implementation context and make sure the feature is ready to merge.

### Step 2: Merge to user branch

Merge the feature branch back to the user branch and switch the working copy to the user branch.

### Step 3: Freeze the feature

Use agent skill `skill-pilot-freeze-core-feature` to freeze the feature into `core/features/`.

### Step 4: Clean up

Delete the feature branch after a successful merge.
