---
name: vibe-coding-project-apply-brainstorm
description: Merge brainstorm ideas from brainstorm.md into a Vibe Coding project's requirements.md. Use when the user wants to apply selected brainstorm ideas to the project requirements.
---

# AI Builder - Apply Brainstorm to Requirements

Merge brainstorm ideas from `brainstorm.md` into the project's `requirements.md`.

## When to Use This Skill

- The project has a `brainstorm.md` with ideas the user wants to incorporate
- The user wants to update requirements based on brainstorm output
- The brainstorm phase is complete and selected ideas should become part of the requirement

## Your Roles in This Skill

- **Project Manager**: Ensure merged requirements stay coherent and well-scoped
- **Technical Writer**: Integrate ideas cleanly into the existing requirement structure

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Read Both Files

Read the project's `brainstorm.md` and `requirements.md` files. Identify the project directory from the brainstorm file path.

### Step 2: Present Ideas for Selection

Summarize the brainstorm ideas and ask the user which ones to apply. If the user has already indicated specific ideas, proceed with those.

### Step 3: Merge Selected Ideas

Integrate the selected brainstorm ideas into `requirements.md`:

- Preserve the existing structure and intent of `requirements.md`
- Add new ideas in the appropriate sections (features, scope, constraints, etc.)
- Avoid duplicating content already present in the requirements
- Keep the language consistent with the existing requirement style

### Step 4: Save and Report

Write the updated content back to `requirements.md`. Summarize what was added or changed.
