# Session Analysis Workflow

Use this reference when the `analyze-user-session` skill is active.

## Core Goals

Analyze every session through these goals:

1. User understanding: the user should understand what they asked the agent to do and what the agent did or planned to do. They should not ask the agent to perform work they cannot basically understand.
2. Agent guidance: the user should guide the agent with effective operating habits, including keeping one agent thread focused on one task instead of mixing unrelated tasks in the same thread.
3. Developer workflow: the user should supervise the agent like a developer, including planning, saved docs, verification, code review, Git branches or worktrees, commits, and remote backup when appropriate.
4. After-action review: the analysis should explain what happened, what worked, what failed or was risky, what the user should ask differently next time, and what reusable checklist or prompt pattern should be kept.
5. Learn-after-doing: the analysis should identify the smallest useful concept the user should learn after the task, enough to supervise similar AI work without memorizing implementation details.

## Step 1: Resolve the Session File

Find the referenced `.jsonl` agent session file from the user prompt. It may be:

- an absolute path
- a repo-relative path such as `.skillpilot/agent-sessions/{file}.jsonl`
- a bare filename under `.skillpilot/agent-sessions/`

If the file cannot be found, ask the user for the correct path. Do not guess across unrelated folders.

The analysis output path must be beside the JSONL file:

```text
{jsonl_stem}_analysis.md
```

Example:

```text
.skillpilot/agent-sessions/20260602T010000Z-codex-session.jsonl
.skillpilot/agent-sessions/20260602T010000Z-codex-session_analysis.md
```

## Step 2: Extract Compact Dialog Context

Do not read the full JSONL directly as the normal path. JSONL session files contain many repeated JSON tokens and can waste the LLM context budget.

Run the extractor script from the repository root:

```bash
core/skills/system/analyze-user-session/scripts/extract_session_context.py {jsonl_file}
```

The script follows the project script convention used by `core/skills/system/explore-showcase/scripts/create-assets.py`: run it from the Skill Pilot project root so it can execute through `core/engine/.venv/bin/python`.

Use the script output as the main dialog-history source. It provides compact session metadata, record counts, referenced paths, user prompts, and shortened agent responses.

Only read targeted parts of the raw JSONL if the compact output is insufficient for a specific question. Do not paste or reproduce the full transcript.

Use the compact output to identify:

- user prompts and follow-up prompts
- agent responses
- session metadata such as agent, model, timestamps, category, `showcase_id`, and `showcase_directory`
- whether the session appears to be a task, coding project, cloud operation, media task, research task, or learning task

Focus on coaching the user. Do not reproduce the full transcript.

## Step 3: Load Task Context

If the session has `showcase_id` or the prompt names a task id, inspect `core/engine/data/` to find the related showcase YAML. Search by `id`, filename, or slug. Use that YAML to understand:

- original task goal
- expected prompt
- tools, skills, technologies, files, and terms
- target directory and task type

If `showcase_directory` exists, inspect that directory to understand the actual project or task result. Keep this read-only.

If the session is not a showcase, infer task context from referenced files, directories, and prompt text.

## Step 4: Optional Read-Only Project Review

When the task produced code, configuration, a web app, cloud setup files, media pipeline, or other inspectable output, do a read-only review when it will improve the coaching.

Look for missed supervision opportunities such as:

- the user delegated work without showing enough baseline understanding of the task, technology, tool, or expected outcome
- the same agent thread was used for multiple unrelated tasks instead of keeping one focused thread per task
- the user did not ask the agent to summarize what happened, what worked, what failed or was risky, and what should change next time
- the user did not ask for reusable prompting patterns, checklists, or review habits that can improve future AI-agent sessions
- the user did not ask what small concept they should learn next to better supervise similar AI work
- the user did not ask the agent to make a plan before implementation
- the user asked for a plan but did not ask the agent to save it to a plan file for later AI or human review
- the user did not provide enough task details, technology direction, constraints, or expected output
- for a website or app build, the user did not specify the listen port, framework, coding language, database, or other core stack, but left the agent to make decisions or give options to choose from
- the user did not provide the right file path, directory, error text, or keywords, causing broad codebase scanning
- for updates and bug fixes, the user did not ask the agent to create a temporary branch or worktree before changing files
- the user did not ask for unit tests, API tests, browser tests, curl checks, build checks, lint checks, or other verification appropriate to the task
- the user did not ask for a code review or risk review before accepting the work
- for task or coding work, the user did not ask the agent to save implementation notes, a summary file, or another durable handoff file
- when a requirement, task, or plan file existed, the user did not ask the agent to update it after changing requirements or plan details, leaving docs out of sync with code
- for prompt-driven updates and fixes, the user did not ask the agent to update related docs, requirements, task files, plan files, implementation notes, or summary files
- for a project, the user did not ask the agent to create a user manual, README, or usage file so the user can remember how to run and use the result
- code or generated files were left uncommitted, or finished work was not pushed to a remote when appropriate, increasing the chance of losing work
- the user asked for a black-box outcome without asking the agent to explain what it did and how to verify it
- the user did not ask for handoff notes, user manuals, runbooks, or next-step learning notes when those would help

Do not modify files. Do not run destructive commands. If running a check would mutate state or require credentials, describe it as a recommended check instead.

## Step 5: Write the Analysis

Write the analysis markdown file with these sections:

```markdown
# Agent Session Analysis

## Session

## Task Background

## What Went Well

## Missed Guidance Opportunities

## Better Prompting Patterns

## Verification and Review Gaps

## Suggested Next Prompt

## Learning Notes
```

Keep feedback practical and direct. The goal is to quickly improve the user's AI-agent operating skill after doing the task.

Prefer examples tied to this exact session. For example:

- Instead of "ask for tests", say which tests fit this task.
- Instead of "provide more context", say which missing file path, technology choice, stack, tool, or constraint would have helped.
- Instead of "ask for a plan", give a short task-specific plan-request sentence the user could reuse.

## Step 6: Report

After writing the file, respond with:

- analysis file path
- top three improvements for the user's AI-agent guidance
- any read-only project review limitation or assumption

Output result as plain text. If the user asked to save it to a file, write it there.
