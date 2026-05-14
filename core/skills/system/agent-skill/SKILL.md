---
name: agent-skill
description: Create, update, find, or dynamically use agent skills. Use when the user asks to create a new skill, edit an existing skill, rename or reorganize skill instructions, find an agent skill, or use a mentioned skill that is not available in the active skill context.
---

# AI Builder - Agent Skill

Create, update, find, and dynamically use agent skills while keeping `SKILL.md` concise and detailed behavior in reference files.

## When to Use This Skill

- The user asks to create, add, or build a new agent skill.
- The user asks to update, edit, rename, reorganize, or improve an existing agent skill.
- The user asks to find and use an agent skill that is not available in the active skill list.
- The user names a skill that cannot be found in the active installed skills, but it may exist in the project skill folders.

## Your Roles in This Skill

- **Project Manager**: Clarify whether the task is create, update, or find/use, and keep the work scoped.
- **Backend Developer**: Create or edit the skill folder structure and validate the result.
- **Technical Writer**: Write concise skill instructions, reference files, descriptions, and outcome reports.
- **QA Engineer**: Verify skill metadata, required sections, references, and installability.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Select the Skill Action

- If creating a new skill, use `references/create.md`.
- If updating, editing, renaming, reorganizing, or fixing an existing skill, use `references/update.md`.
- If the user asks to find and use an agent skill, or if a user-mentioned skill is not installed in the active skill list, use `references/find.md`.

### Step 2: Load the Needed Reference

Open only the reference file for the selected action. Load additional files only when that reference explicitly requires them.

### Step 3: Perform the Action

Follow the selected reference. Keep new skill details inside the skill folder, and put temporary/intermediate files under `.skillpilot/temp/` if they are needed.

### Step 4: Verify and Report

Run the verification steps required by the selected reference. Report the skill name, path, files changed, verification result, and any assumptions.

## Expected Output

- For create: a new valid agent skill folder with `SKILL.md` and relevant references.
- For update: an updated valid agent skill folder with behavior preserved or intentionally changed.
- For find: the matched skill folder, metadata summary, and use of the matched `SKILL.md` as the active skill instructions for the task.
