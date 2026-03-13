---
name: skill-pilot-feature-review
description: Review a Skill Pilot feature implementation for bugs, regressions, and missing tests. Use when a feature implementation should be audited before merge.
---

# AI Builder - Skill Pilot Feature Review

Review a feature implementation with a code-review mindset.

## When to Use This Skill

- The implementation should be audited
- The user wants review findings

## Your Roles in This Skill

- **Code Reviewer**: Identify bugs and regressions
- **Project Manager**: Keep findings scoped to the feature

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Read the implementation context

Read the referenced implementation file and inspect the code.

### Step 2: Report findings first

List bugs, risks, and missing tests before any summary.
