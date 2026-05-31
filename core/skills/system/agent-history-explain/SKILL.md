---
name: agent-history-explain
description: Export an agent session history to a markdown file, then write a beginner-friendly explain.md alongside it that teaches a new coder how the user instructed the AI agent.
---

# Agent History + Beginner Explanation

Turn a recorded agent session into two paired files at a user-specified destination:

1. **`<name>.md`** — raw human-readable history (produced by `core/bin/agent-history`).
2. **`<name>-explain.md`** — a beginner-friendly walkthrough that teaches a code newcomer how to instruct an AI agent, using the real prompts from the history as examples.

## When to Use This Skill

- The user asks to "export an agent history and explain it" / "create a tutorial from this session".
- The user references a recorded session (a session id, a session file name, or a path under the project's agent history) and asks for both the raw export and a beginner-oriented explanation.
- The user wants to teach a non-coder (a junior, a student, a colleague new to AI tools) how to drive an AI coding agent, using real examples.

Do **not** use this skill for:
- Just exporting a session with no teaching goal — call `core/bin/agent-history` directly.
- Reviewing or critiquing the agent's code output — use a code-review skill instead.

## Your Roles in This Skill

- **Archivist**: Run `core/bin/agent-history` and place the raw export at the requested path.
- **Teacher**: Read the exported history and distill it into a beginner-friendly explanation in `explain.md`.
- **Translator**: Detect the language of the original user prompts and write the explanation in that language (English by default).

## Role Communication

Announce each role before acting:

`As a {Role}, I will {action description}`

## Inputs

The user must provide (ask if missing):

- **session reference** — a session id substring **or** a session file name. The skill resolves it against `.skillpilot/agent-sessions/` (see Step 1).
- **destination path** — a directory or a base file path where the two files should be written. If only a directory is given, derive the base name from the session.

Optional:
- **language** — explicit override (e.g. "write the explain file in Chinese"). If absent, follow the Language Selection rule below.
- **audience** — e.g. "for a complete beginner", "for a junior dev". Default: complete coding beginner.

## Workflow

### Step 1 — Locate the session file

Look inside `.skillpilot/agent-sessions/` for a file whose name contains the user's reference (session id substring or file name). Session files are named like `<timestamp>-<agent>-<session-id>.jsonl`.

- If exactly one match: use it.
- If multiple matches: list them and ask the user to pick.
- If none: report the miss and ask the user to clarify; do not guess.

### Step 2 — Export the dialog file

Refer to `references/agent-history-cli.md` for how to use `./core/bin/agent-history`.

Run the CLI with the resolved file name (or id substring):

```bash
./core/bin/agent-history <reference> > <destination>/<base>.md
```

Write its markdown output to `<destination>/<base>.md`. Confirm the file exists and is non-empty before proceeding.

### Step 3 — Light spelling and grammar pass on user prompts only

Open `<base>.md` and fix **only** clear spelling and grammar errors **inside the user prompt sections**. Leave everything else untouched.

**Scope — fix only user prompts:**

- Apply fixes only to the text the user wrote (the `## user_prompt` / "user:" blocks, depending on the export format).
- Do **not** edit any agent response, agent reasoning, tool call, tool output, or system message — even if you spot a typo there.

**Strict rules — preserve the original record:**

- Do **not** rewrite, paraphrase, expand, shorten, restructure, or reorder anything.
- Do **not** translate.
- Do **not** touch code blocks, command lines, file paths, identifiers, or anything inside backticks — even inside user prompts.
- Do **not** "improve clarity" or "make it more professional" — leave casual phrasing, tone, and quirks intact.
- If a sentence is grammatically wrong but the meaning is unclear, leave it alone rather than guess.

The goal is a faithful, easily-readable transcript — not a polished essay.

### Step 4 — Read and understand the (now-cleaned) dialog

Read the dialog end-to-end. Identify:

- Each user prompt (the actual instructions issued).
- What the agent did in response (the high-level outcome, not the full diff).
- Patterns worth teaching: clear instructions, corrections, rule updates, references to files, iteration loops.

### Step 5 — Detect the language

Apply the **Language Selection** rule (see below) to choose the language of the explain file.

### Step 6 — Write the explain file

Write `<destination>/<base>-explain.md` following the **Explain File Structure** below. The explain file is **based on the cleaned dialog file from Step 3** — quote prompts verbatim from it, then translate or paraphrase if the explanation language differs.

### Step 7 — Report

List both created files with absolute paths, the count of spelling/grammar fixes applied in Step 3, and a one-line summary of each file.

## Language Selection

- **Default:** English.
- **Override:** If the user explicitly requests a language, use it.
- **Auto-switch:** If the original user prompts in the history are predominantly written in a non-English language (Chinese, Japanese, Spanish, etc.), write `explain.md` in that language. Beginners learn best in their native language, and the prompts already reveal the user's working language.
- When in doubt between two languages, ask the user once.

## Explain File Structure

The explain file is a **teaching artifact**, not a summary. Target a reader who has never instructed an AI coding agent before.

Recommended sections (adapt to fit the session — do not pad if a section adds no value):

1. **Intro** — one paragraph: what the original session accomplished, and what the reader will learn from it.
2. **Key concepts** — short table of 2–4 terms the reader needs (Agent, Skill, Prompt, etc.). Define in plain words.
3. **Walkthrough of the real prompts** — for each user prompt in the history:
   - Quote the original prompt verbatim.
   - If the explain language differs from the prompt language, provide a translation.
   - Extract 1–3 lessons in bullet form (what the beginner should notice and copy).
4. **Golden rules** — 3–7 reusable principles distilled from the session (e.g. "put long details in a file, not in the prompt", "turn one-off corrections into permanent rules").
5. **Closing line** — one memorable sentence the reader can take away.

### Writing rules for `explain.md`

Refer to `<base>.md`, then create a file that explains how the user instructed the AI agent to do the work in this task. Name the file `<base>-explain.md`, and target a code beginner who is learning how to use AI for coding.

Also follow these rules:

- Address the reader directly ("you").
- Prefer concrete examples from the history over abstract advice.
- Show *contrast* when useful: a bad version of a prompt vs. the good version actually used.
- Keep paragraphs short. Use tables and bullet lists.
- Do **not** include code diffs or implementation detail from the session — the focus is *how to instruct the agent*, not *what code was written*.
- Do **not** include generic AI-safety reminders or operating policy.

## Validation

Before reporting done:

- Both files exist at the requested path.
- `<base>.md` was produced by `core/bin/agent-history` (do not hand-write it).
- `<base>-explain.md` references at least one real prompt from the history.
- The explain file's language matches the Language Selection rule.
