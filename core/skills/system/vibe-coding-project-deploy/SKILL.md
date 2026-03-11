---
name: vibe-coding-project-deploy
description: Deploy a Vibe Coding project implementation using its implement.md context and deployment requirements. Use when the user wants the project deployed to a production environment.
---

# AI Builder - Vibe Coding Project Deploy

Deploy a Vibe Coding project to the user's chosen production environment.

## When to Use This Skill

- The user asks to deploy the project
- The implementation is ready for deployment
- The project needs to be released to a production environment

## Your Roles in This Skill

- **DevOps Engineer**: Prepare the deployment steps
- **Backend Developer**: Confirm runtime needs and app startup
- **Project Manager**: Keep the rollout aligned with the requirement

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Implementation Context

Read the referenced `implement.md` and identify the deployment target, runtime, and dependencies.

### Step 2: Determine the Deployment Target

If no deployment target is specified in `requirements.md`, `plan.md`, or `implement.md`, ask the user how and where they want to deploy to production before proceeding.

### Step 3: Prepare and Deploy

Confirm the app start command, environment requirements, exposed ports, and release steps. Use the appropriate deployment tools and infrastructure for the chosen target. Do not assume credentials or infrastructure already exist.

### Step 4: Report the Outcome

Summarize what was deployed, where it was deployed, and any remaining setup items.
