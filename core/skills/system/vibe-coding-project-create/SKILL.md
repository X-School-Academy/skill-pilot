---
name: vibe-coding-project-create
description: Create a Vibe Coding project requirement from a prompt by creating workspace/vibe-coding/{project-name}/requirements.md. Use when a user wants to start a new coding project from a short request instead of filling the WebUI form.
---

# AI Builder - Vibe Coding Project Create

Create a new Vibe Coding project folder and write its initial `requirements.md`.

## When to Use This Skill

- The user wants to start a new Vibe Coding project from a prompt
- The project does not yet have a `requirements.md`
- The user wants a quick project bootstrap before planning

## Your Roles in This Skill

- **Project Manager**: Choose a safe project folder name and keep the structure consistent
- **Technical Writer**: Turn the user's prompt into a clean `requirements.md`

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Determine the Project Name

Derive a concise kebab-case project name from the user's request if none is provided.

### Step 2: Create the Project Folder

Create `workspace/vibe-coding/{project-name}/` if it does not already exist.

### Step 3: Write the Requirement

Create `workspace/vibe-coding/{project-name}/requirements.md` with the user's request in clear English. Keep it requirement-focused and avoid implementation details.

### Step 4: Report the Result

Tell the user which folder and file were created.
