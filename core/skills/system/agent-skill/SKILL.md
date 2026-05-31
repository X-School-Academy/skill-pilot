---
name: agent-skill
description: Create, update, find, or dynamically use agent skills and Skill Pilot subagents. Use when the user asks to create or edit a skill, create or edit a subagent, rename or reorganize instructions, find an agent skill, find a subagent, or use a mentioned skill or subagent that is not active.
---

# AI Builder - Agent Skill

Create, update, find, and dynamically use agent skills and Skill Pilot subagents while keeping source instructions concise and detailed behavior in reference files.

## When to Use This Skill

- The user asks to create, add, or build a new agent skill.
- The user asks to update, edit, rename, reorganize, or improve an existing agent skill.
- The user asks to create, add, or build a Skill Pilot subagent.
- The user asks to update, edit, rename, disable, remove, or improve an existing Skill Pilot subagent.
- The user asks to find and use an agent skill that is not available in the active skill list.
- The user asks to find or inspect a subagent.
- The user names a skill or subagent that cannot be found in the active context, but it may exist in the project folders.

## Your Roles in This Skill

- **Project Manager**: Clarify whether the task is about a skill or subagent, select create/update/find, and keep the work scoped.
- **Backend Developer**: Create or edit skill and subagent source files and run installers.
- **Technical Writer**: Write concise instructions, reference files, descriptions, prompts, and outcome reports.
- **QA Engineer**: Verify metadata, required sections, generated files, references, and installability.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Select the Artifact Type

- If the task is about an agent skill, use `references/skill.md`.
- If the task is about a Skill Pilot subagent, use `references/agent.md`.
- If the user says "agent" ambiguously, inspect the task wording:
  - Use `references/agent.md` when they mention subagents, code-agent subagent folders, `.claude/agents`, `.codex/agents`, `.gemini/agents`, `.opencode/agents`, or `core/subagents`.
  - Use `references/skill.md` when they mention skills, `SKILL.md`, skill folders, skill installation, or dynamic skill loading.

### Step 2: Load the Needed Reference

Open only `references/skill.md` or `references/agent.md` first. Then open only the action-specific reference that file routes to, such as `skill-create.md` or `agent-update.md`.

### Step 3: Perform the Action

Follow the selected references. Keep new skill details inside skill folders, keep new subagent details inside `core/subagents/system/` or `core/subagents/user/`, and put temporary/intermediate files under `.skillpilot/temp/` if they are needed.

### Step 4: Verify and Report

Run the verification steps required by the selected reference. Report the skill or subagent name, path, files changed, verification result, and any assumptions.

## Expected Output

- For skill create: a new valid agent skill folder with `SKILL.md` and relevant references.
- For skill update: an updated valid agent skill folder with behavior preserved or intentionally changed.
- For skill find: the matched skill folder, metadata summary, and use of the matched `SKILL.md` as active instructions when requested.
- For subagent create or update: a valid source Markdown file under `core/subagents/system/` or `core/subagents/user/`, plus generated code-agent files after install.
- For subagent find: the matched subagent source path, metadata summary, and installed target status when relevant.
