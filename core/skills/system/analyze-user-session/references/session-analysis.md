# Session Analysis Workflow

Use this reference when the `analyze-user-session` skill is active.

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

## Step 2: Read the Dialog History

Read the JSONL records and identify:

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

- the user did not ask the agent to make a plan before implementation
- the user did not provide enough task details, technology direction, constraints, or expected output
- the user did not provide the right file path, directory, error text, or keywords, causing broad codebase scanning
- the user did not ask for unit tests, API tests, browser tests, curl checks, build checks, lint checks, or other verification appropriate to the task
- the user did not ask for a code review or risk review before accepting the work
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
