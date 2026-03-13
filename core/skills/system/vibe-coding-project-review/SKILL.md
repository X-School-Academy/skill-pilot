---
name: vibe-coding-project-review
description: Review the implementation of a Vibe Coding project using its implement.md context and current code. Use when the user wants bug risks, regressions, and missing tests identified.
---

# AI Builder - Vibe Coding Project Review

Review a Vibe Coding project implementation with a code-review mindset.

## When to Use This Skill

- The user asks to review the implementation
- The project has implementation context in `implement.md`
- Bugs, regressions, and missing tests should be identified

## Your Roles in This Skill

- **Code Reviewer**: Find defects and risks
- **Project Manager**: Keep the review tied to the requested scope

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Implementation Context

Read the referenced `implement.md` and inspect the relevant code paths.

### Step 2: Review for Findings

Prioritize correctness issues, regressions, unsafe assumptions, and missing verification.

### Step 3: Report Findings First

List findings ordered by severity, then add open questions or residual risks.
