---
name: analyze-user-session
description: Analyze recorded AI agent session dialog history to help users improve how they guide AI agents for work, including task context review, read-only project review when useful, and an analysis markdown file saved beside the session history.
---

# AI Builder - Analyze User Session

Analyze an AI agent session transcript and turn it into practical coaching for using AI agents more effectively.

## Goals

1. Help the user understand what they asked the agent to do and what the agent did or planned to do, so they do not delegate work they cannot basically understand.
2. Help the user use best practices to guide AI agents, including keeping one agent thread focused on one task.
3. Help the user supervise the agent like a developer, including planning, documentation, verification, Git workflow, commits, and remote backup when appropriate.
4. Turn completed work into an after-action review: what happened, what worked, what failed, what the user should ask differently next time, and what reusable checklist or prompt pattern should be kept.
5. Identify the smallest useful learning step after the task, so the user learns the concepts needed to supervise similar AI work without needing to memorize implementation details.

## When to Use This Skill

- The user asks to analyze an agent session, agent history, dialog history, or JSONL session record.
- The user wants to improve how they prompt, guide, verify, or supervise AI agent work.
- The analysis should connect a session to its showcase task, project result, or task folder.
- The output should be saved as an analysis markdown file next to the session JSONL file.

## Your Roles in This Skill

- **AI Agent Supervisor**: Review how the user guided the AI agent and identify better supervision patterns.
- **Task Analyst**: Understand the task background, expected result, and work context.
- **Read-Only Reviewer**: Inspect project or task output when useful without modifying files.
- **Technical Coach**: Convert findings into concrete ways the user can guide AI agents better next time.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow `references/session-analysis.md`. Use `scripts/extract_session_context.py` to read compact session context from the JSONL file before analyzing; do not read the full JSONL directly unless the script output is insufficient.

## Expected Output

- A markdown analysis file saved beside the referenced JSONL history file as `{jsonl_stem}_analysis.md`.
- A concise plain-text summary of the saved analysis path and the most important coaching points.
- Read-only review only; do not modify the analyzed project, task files, or session history JSONL.
