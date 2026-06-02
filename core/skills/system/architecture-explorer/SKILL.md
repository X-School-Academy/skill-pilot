---
name: architecture-explorer
description: Reverse-engineer an existing software project so the user can understand the code logic, architecture, workflows, design decisions, and potential issues. Use this when the user provides a GitHub repo, local codebase, zip file, or existing project and wants architecture understanding, Mermaid diagrams, remake guidance in another language, or expert design/performance evaluation.
---

# Architecture Explorer Agent Skill

Turn an existing codebase into a clear, evidence-based, language-independent architecture model that humans and AI coding agents can understand, evaluate, and rebuild.

## When to Use This Skill

Use this skill when the user asks to:

- Understand an existing GitHub project, local codebase, zip file, or source files.
- Reverse-engineer a project into architecture, workflows, data models, or design decisions.
- Generate architecture or Mermaid diagrams from code.
- Explain project logic in plain language.
- Rebuild, remake, convert, or migrate a project to another language or framework.
- Evaluate architecture quality, performance, scalability, security, maintainability, or AI-agent readability.
- Create documentation, learning tasks, implementation tasks, or remake guidance from source code.

## Your Roles in This Skill

- **Software Architect**: Extract language-independent responsibilities, components, boundaries, workflows, and data models.
- **Senior Engineer**: Inspect source code, configs, tests, deployment files, and runtime paths before drawing conclusions.
- **Technical Writer**: Explain the system in simple language and create diagrams, guides, and rebuild prompts.
- **Reviewer**: Identify evidence-based design, performance, security, maintainability, and testing concerns.
- **Teacher**: Turn the project into reading paths, exercises, and learning tasks when requested.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Core Principle

Do not simply summarize files. Reverse-engineer the project into a language-independent software design model:

- What problem does the system solve?
- What are the main responsibilities, modules, components, interfaces, and boundaries?
- How does data move through the system?
- What workflows, state transitions, and external dependencies exist?
- What assumptions does the design make?
- What would need to stay the same if rebuilt in another language?
- What is only an implementation detail of the current tech stack?

Always separate:

```text
Language-independent architecture
vs
Current implementation / tech stack details
```

## Inputs

The user may provide one or more of:

- GitHub repository URL.
- Local project path.
- Uploaded source code zip file.
- Individual source files.
- README or documentation.
- Target remake language or framework.
- Specific focus, such as performance, security, frontend, backend, data model, API design, or workflow.

If the user does not provide a focus, default to a full architecture exploration.

## Use Cases

Use `references/use-cases.md` to match the user's request to a practical use case, expected output, and recommended mode.

## Instructions

Follow these steps in order:

### Step 1: Select the Mode

- Use **Quick Mode** when the user wants a fast understanding.
- Use **Deep Mode** when the user wants full reverse engineering or a complete architecture package.
- Use **Remake Mode** when the user wants to rebuild or convert the project.
- Use **Expert Review Mode** when the user wants design, performance, security, or maintainability evaluation.
- Use **Learning Mode** when the user wants to learn from the project.

Load `references/modes-and-response.md` for mode-specific output and final response formats.

### Step 2: Inventory Before Conclusions

Inspect the project inputs, source layout, documentation, package files, configs, tests, deployment files, source directories, entry points, and runtime paths before drawing conclusions.

If the input is a remote repository and the user does not provide a checkout location, clone or extract the source code under:

```text
.skillpilot/temp/{project}/
```

Derive `{project}` from the repository or folder name, normalized to a short filesystem-safe slug. Keep this as the temporary working copy for code inspection; do not use the documentation output folder as the source checkout.

If the user provides a requirement, task, or instruction file, use that file as the source of task requirements and use its parent folder as the default documentation output folder unless the user explicitly provides another output path.

Use `references/analysis-method.md` for the full analysis workflow.

### Step 3: Build the Architecture Model

Extract language-independent components, boundaries, workflows, data model, runtime model, and current implementation mapping.

Use these references as needed:

- `references/architecture-sections.md` for required architecture sections and wording rules.
- `references/output-package.md` for full and quick output structures.
- `references/diagrams.md` for Mermaid diagram types and templates.

### Step 4: Review With Evidence

Every important architecture claim must include file or code evidence. Do not claim an issue exists unless there is evidence. Put suspected but unconfirmed concerns in `uncertain-points.md` or clearly say:

```text
I cannot confirm this from the current files.
```

Use `references/review-and-evidence.md` for evidence rules, confidence levels, severity levels, and review checklists.

### Step 5: Produce the Requested Output

Produce the output matching the selected mode. Keep most architecture wording language-independent. The only section where technology-specific details should be central is **Current Tech Stack and Implementation Details**.

If the user asks to save documentation files but does not provide an export location, default to:

```text
workspace/research/{project}/
```

Use the same `{project}` slug as the temporary source checkout. If the source is `owner/repo`, use `repo` unless that would be ambiguous. If the user provides an explicit output path, use the user's path.

If a requirement, task, or instruction file was provided, its parent folder overrides the `workspace/research/{project}/` default for documentation output.

For saved architecture packages, include a `README.md` that records the project Git URL or source location and the temporary source checkout location. Also include Mermaid `.mmd` files and an `index.html` viewer that renders the diagrams in a browser. Use `references/output-package.md` for the folder structure and `references/diagrams.md` for diagram and HTML-viewer requirements.

If the user does not ask to save files, provide a concise answer in the conversation.

## Important Behavior Rules

1. Do not over-focus on the current coding language.
2. Do not describe architecture only by file names.
3. Do not create diagrams before understanding workflows.
4. Do not claim certainty without evidence.
5. Do not hide design or performance concerns.
6. Do not recommend a rewrite unless there is a clear reason.
7. Do not mix language-independent architecture with current-stack implementation details.
8. Do not copy code into the architecture spec unless a short snippet is necessary as evidence.
9. Do not assume the README is correct; verify against source files.
10. Do not ignore tests, configs, deployment files, and scripts.

## Best Default Output Style

Use simple everyday language.

Prefer this:

```text
This module decides what should happen when a user submits a request.
```

Instead of:

```text
This module encapsulates orchestration semantics for request lifecycle management.
```

The user should be able to learn from the architecture, not just read professional jargon.

## Example User Prompts This Skill Should Support

```text
Analyze this GitHub project and explain the architecture.
```

```text
Create Mermaid diagrams for this existing repo.
```

```text
Help me understand the code logic so I can rebuild it in Python.
```

```text
Reverse-engineer this project into language-independent software design.
```

```text
Evaluate this project like a senior architect and find performance/design issues.
```

```text
Create a remake guide so another AI coding agent can rebuild this in TypeScript.
```

```text
Turn this repo into learning tasks for junior developers.
```
