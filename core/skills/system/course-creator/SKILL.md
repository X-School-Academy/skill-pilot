---
name: course-creator
description: Create interactive courses and assignments for students in the project's markdown format. Use when asked to create a new course, educational module, or assignment.
---

# AI Builder - Course Creator

This skill creates structured, engaging educational content using the project's specialized markdown block system. It supports two distinct course formats. If the requested format is unclear, default to `guided_challenge` for online interactive tutorial courses.

## When to Use This Skill

- User wants to create a new educational course, module, or assignment.
- User wants to design a quiz, walkthrough, or interactive tutorial.
- User provides a topic and asks for a structured learning path.
- User needs to update an existing course with new interactive elements.

## Your Roles in This Skill

- **Product Manager**: Define the course goal, audience, duration, and the appropriate course type.
- **Technical Writer**: Draft content with clarity, accuracy, and a tone that matches the audience.
- **Project Manager**: Structure content into a coherent sequence of sections or steps.
- **Backend Developer**: Implement interactive elements using the specialized markdown blocks.

## Role Communication

Announce your actions before performing them using:

> As a {Role} [and {Role}, ...], I will {action description}

## Two Supported Course Types

The first decision is which format fits the task. Use an explicit user request when one is provided. If the user asks for an online interactive tutorial course but does not state a type, default to `guided_challenge`.

### Type 1: `guided_challenge` (step-gated assignment)

A staged, app-driven assignment rendered by `course.block.tsx`. Every visible piece of content lives **inside a fenced code block**; narration outside fences is ignored. Steps advance via control blocks, quizzes gate progression, terminal commands can be validated server-side, and progress is tracked.

Use this when the learner should be walked through a sequence with checkpoints (interactive coding, terminal validation, forms, container provisioning, etc.).

**File location:** `workspace/learning/{slug}.md` by default. If the user or calling tool provides an explicit output file path, write the course to that exact path instead.

**Required first block** — a yaml meta fence. Add `type: guided_challenge` to declare the course type:

````markdown
```yaml {"type":"meta"}
title: "Your Course Title"
slug: your-course-slug
type: guided_challenge
duration: 30 minutes
id: 1
token: your-token
```
````

After the meta block, every step is a fenced block. Common ones:
- `markdown {"during":1000}` — reading section (auto-advances after delay).
- `markdown {"type":"control","action":"continue","timeLeft":0}` — gate progress.
- `markdown {"type":"control","action":"submit"}` — final submission.
- `markdown {"type":"control","action":"end"}` — closing message.
- `markdown {"type":"control","action":"use_skill","skill_name":"..."}` — invoke an agent skill.
- `markdown {"type":"bash"}` / `markdown {"type":"vscode"}` — clickable shell / editor actions.
- `python|javascript|... {"type":"code","action":"run"}` — interactive editor + runner.
- `tabs {...}` — multiple code editors under tabs.
- `yaml {"type":"form","ref":"ask"}` — quiz (radio / checkbox / text / select / textarea).
- `yaml {"type":"list"}` / `yaml {"type":"media"}` / `yaml {"type":"notebook"}` — supporting blocks.
- `memory-card {"title":"..."}` — flip-card recall set.
- `slides {...}` — horizontal carousel of nested blocks.

**Escaping:** any inner triple-backticks inside a fenced step must be written as `\`\`\`` (escaped). The renderer unescapes them.

See `references/sample-guided-challenge.md` (in this skill folder) for a working `guided_challenge` reference.

### Type 2: `interactive_tutorial` (rich article with interactive blocks)

A flowing, readable article rendered as normal markdown, with **inline interactive code blocks** scattered through the prose. There is no step gating; the learner scrolls, reads, runs code, and explores tabs at their own pace.

Use this when the goal is to teach or showcase concepts in a narrative, encyclopedic, or comparative way (e.g., "Hello World in 12 languages", "Syntax differences across languages", reference material with runnable examples).

**File location:** `workspace/learning/{slug}.md` by default. If the user or calling tool provides an explicit output file path, write the tutorial to that exact path instead, including paths under `.skillpilot/temp/` for generated intermediate artifacts.

**Required header** — a YAML **frontmatter** block delimited by `---` (NOT a fenced `yaml` code block). It must be the very first content in the file:

```markdown
---
title: "Your Tutorial Title"
slug: your-tutorial-slug
type: interactive_tutorial
duration: 30 minutes
id: 1
token: your-token
---
```

After the frontmatter, write **normal markdown** — headings, paragraphs, lists, images. Interactive elements go inline as standard fenced code blocks with meta:

- ` ```dart {type:code, action: run} ` — runnable code snippet (any supported language: `dart`, `javascript`, `typescript`, `python`, `php`, `swift`, `java`, `kotlin`, `c`, `cpp`, `objective-c`, `go`, `react`, `flutter`, etc.).
- ` ```tabs ` or ` ```tabs {rawCode: true} ` — multiple code variants under tabs; inner fences must be escaped as `\`\`\``.
- ` ```yml-list {default: true} ` — bulleted list with optional Ask-AI affordances per item.
- Plain ` ```language ` fences render as static (non-interactive) code samples.

Do not use control blocks (`type:control`), step gating, `during`, or `submit` in this format — those are exclusive to `guided_challenge`.

See `references/sample-interactive-tutorial.md` (in this skill folder) for a working `interactive_tutorial` reference.

## Block Reference

For every supported block (meta fields, optional flags, language list, VS Code event contract): see `core/webui/docs/markdown-block-docs.md`.

## Instructions

### Step 1 — Define the Foundation

As a **Product Manager**:
1. Determine the **course type** (`guided_challenge` vs `interactive_tutorial`). If the user did not specify one, default online interactive tutorial courses to `guided_challenge`.
2. Define the **goal**: what should the student be able to DO afterward?
3. Identify the **audience** (e.g., high-schooler, beginner dev, professional).
4. Set a realistic **duration** (20–30 min minimum for a guided challenge; tutorials can be longer).

### Step 2 — Research and Content Mapping

As a **Technical Writer**:
1. Research the topic for current best practices and common pitfalls.
2. Map key concepts.
3. Identify the right interactive opportunities for the chosen format (forms + validation for `guided_challenge`; inline runnable snippets / tabs for `interactive_tutorial`).

### Step 3 — Design the Structure

As a **Project Manager**:
- `guided_challenge`: sequence as Intro → Theory → Practice (gated) → Assessment → Conclusion.
- `interactive_tutorial`: structure as Objectives → numbered or themed sections → inline examples → Summary.

### Step 4 — Author the File

As a **Backend Developer**, write the file at the explicit output path if one was provided; otherwise write it at `workspace/learning/{slug}.md` using the format for the chosen type.

Required header rules:
- `guided_challenge` → first fenced block: ` ```yaml {"type":"meta"} ` ... ` ``` ` with `type: guided_challenge`.
- `interactive_tutorial` → frontmatter `---` ... `---` with `type: interactive_tutorial`.

### Step 5 — Final Review

As a **Technical Writer**, verify:
- The correct header format is used for the chosen `type`.
- Inner triple-backticks are escaped as `\`\`\`` wherever they appear inside another fenced block.
- Code samples are accurate and runnable.
- Tone matches the audience.

## Key Principles

- **Right format for the job:** narrative reference → `interactive_tutorial`; gated assignment with validation → `guided_challenge`. Don't mix paradigms (no control blocks in a tutorial; no frontmatter in a challenge).
- **Interactivity first:** prefer runnable code, tabs, forms, and memory cards over walls of prose.
- **Escape inner fences** as `\`\`\``.
- **Student-centric:** language and examples must match the declared audience level.
- **Conciseness:** in `guided_challenge`, keep each step short and use `during` to pace.
