---
name: vibe-coding-project-brainstorm
description: Brainstorm ideas, alternatives, and enhancements for a Vibe Coding project requirement. Use when a project requirements.md needs creative exploration before planning.
---

# AI Builder - Vibe Coding Project Brainstorm

Generate creative ideas, alternative approaches, and enhancements for an existing Vibe Coding `requirements.md`.

## When to Use This Skill

- The user wants to explore ideas before committing to a plan
- The project has a `requirements.md` that could benefit from creative expansion
- The user wants to consider alternative approaches or additional features

## Your Roles in This Skill

- **Creative Strategist**: Generate diverse ideas and alternative approaches
- **Technical Advisor**: Assess feasibility and trade-offs of each idea
- **Project Manager**: Keep suggestions aligned with the project's core intent

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Requirement File

Read the referenced `requirements.md` and understand the project's goals, scope, and constraints.

### Step 2: Brainstorm Ideas

Generate ideas across these categories:

1. **Alternative Approaches**: Different ways to achieve the same goals
2. **Feature Enhancements**: Additional capabilities that complement the core requirement
3. **Technical Options**: Different technology choices or architecture patterns
4. **UX Improvements**: Better user experience ideas
5. **Risk Mitigations**: Potential issues and how to address them early

For each idea, briefly note its benefit and any trade-off.

### Step 3: Save and Present

Save the brainstorm as `brainstorm.md` in the same project directory as `requirements.md` (i.e., `workspace/vibe-coding/{project-name}/brainstorm.md`). Create the file if it doesn't exist, or update it if it does.

Present the brainstormed ideas in a structured format. Ask the user which ideas they want to incorporate into the requirements.
