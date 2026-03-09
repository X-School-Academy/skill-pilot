---
name: vibe-coding-project-deploy
description: Deploy a Vibe Coding project implementation using its implement.md context and deployment requirements. Use when the user wants the project deployed, including a first-pass AWS EC2 deployment path when appropriate.
---

# AI Builder - Vibe Coding Project Deploy

Deploy a Vibe Coding project, with AWS EC2 as the default first-pass deployment target when that matches the requirement.

## When to Use This Skill

- The user asks to deploy the project
- The implementation is ready for deployment
- AWS EC2 is the intended first deployment target

## Your Roles in This Skill

- **DevOps Engineer**: Prepare the deployment steps
- **Backend Developer**: Confirm runtime needs and app startup
- **Project Manager**: Keep the rollout aligned with the requirement

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Read the Implementation Context

Read the referenced `implement.md` and identify the deployment target, runtime, and dependencies.

### Step 2: Prepare the Deployment Plan

Confirm the app start command, environment requirements, exposed ports, and release steps.

### Step 3: Deploy Safely

If AWS EC2 is in scope, use the appropriate EC2-related project skills and infrastructure steps. Do not assume credentials or infrastructure already exist.

### Step 4: Report the Outcome

Summarize what was deployed, where it was deployed, and any remaining setup items.
