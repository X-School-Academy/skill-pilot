---
name: skill-pilot-freeze-core-feature
description: Create or update files under core/features/ from user instructions and project inspection. Use when a user wants to freeze a core feature
---

# AI Builder - Skill Pilot Freeze Core Feature

Create or update a compact feature file in `core/features/` so users and AI agents can quickly understand a feature and locate related code.

## When to Use This Skill

- The user wants to create a new feature file under `core/features/`
- The user wants to freeze current product behavior into a reusable feature reference
- A feature file is missing, outdated, or too vague for AI-assisted development

## Your Roles in This Skill

- **Product Manager**: Define the feature from a user-facing perspective and keep scope at feature level instead of low-level implementation detail.
- **Technical Writer**: Produce concise markdown that is easy to scan and efficient for LLM context windows.
- **Project Manager**: Keep naming, file placement, and coverage consistent with the feature knowledge base.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Key Principles

- Treat each feature as a user-level capability unless it is clearly technical-only.
- Keep each feature file small enough for efficient LLM use.
- Prefer linking to related feature files instead of repeating large amounts of detail.
- Include enough code keywords that an agent can locate relevant code with `find`, `grep`, `rg`, `sed`, or `cat`.
- Use file paths relative to the project root only. Do not include line numbers.
- Use sub-feature files only when the parent feature would otherwise become too large.

## Expected Output

- One markdown file under `core/features/` named with lowercase letters and hyphens only
- If needed, a sub-feature file using `feature-name--sub-feature-name.md`
- Content that includes:
  - A short feature brief
  - User-facing scope or behavior summary
  - Related feature file names for adjacent or dependent behavior
  - Code references using project-root-relative file paths, function names, and search keywords only

## Instructions

Follow these steps in order:

### Step 1: Understand the requested feature

- Read the user's instruction and identify the feature to freeze.
- If the user gives a broad area instead of a precise feature, inspect the relevant UI, docs, and source code to identify the user-facing feature boundary.
- Prefer one feature per file. Create a sub-feature only when the behavior is large enough to justify separate documentation.

### Step 2: Inspect the project before writing

- Read the relevant docs and source files needed to understand the feature.
- Check existing files in `core/features/` to avoid duplicates and to match naming patterns.
- When mapping the feature to code, collect only compact references:
  - project-root-relative file paths
  - function names
  - component names
  - API route names
  - distinctive keywords useful for `rg`

### Step 3: Choose the target file name

- Use lowercase letters and hyphens only.
- Use the base form `feature-name.md` for normal features.
- Use `feature-name--sub-feature-name.md` for sub-features.
- Do not include spaces, uppercase letters, underscores, or line-based identifiers.

### Step 4: Write the feature file in `core/features/`

Create or update `core/features/{feature-name}.md` with concise sections such as:

- `# Feature Name`
- `## Brief`
- `## User Value`
- `## Main Behavior`
- `## Related Features`
- `## Code References`

Content rules:

- `Brief` must be short and understandable by a non-technical user.
- Focus on what the feature does, not internal implementation history.
- Keep bullets compact and information-dense.
- `Related Features` is required when adjacent flows, dependencies, or companion screens exist.
- Use `Related Features` to point to other feature files instead of copying their details into the current file.
- `Code References` must include only:
  - file paths relative to project root
  - function, component, route, class, or keyword names
- Never include line numbers.
- Avoid copying large code or long excerpts.

### Step 5: Keep the file optimized for AI retrieval

- Remove filler text and repeated statements.
- Prefer stable search terms over prose-heavy explanations.
- Move cross-feature detail into `Related Features` references instead of expanding the current file.
- If the file becomes too large, split part of it into one or more sub-feature files using the double-hyphen naming rule.
- Make sure the final document is small enough to fit comfortably in an LLM context window.

### Step 6: Verify the result

- Confirm the file is under `core/features/`.
- Confirm the file name follows the lowercase-and-hyphen rule.
- Confirm the feature is described at user level unless it is truly technical-only.
- Confirm related behavior is referenced through `## Related Features` instead of duplicated in full.
- Confirm code references use root-relative paths and keywords only.
- Confirm there are no line numbers and no oversized sections.

## Common Issues

- If the request is too broad, split it into multiple feature files instead of creating one oversized file.
- If the code is incomplete or ambiguous, document the current observable behavior and note uncertainty briefly.
- If an older file exists with overlapping scope, update it instead of creating a duplicate.
