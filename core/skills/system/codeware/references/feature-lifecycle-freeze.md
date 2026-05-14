# Feature Lifecycle: Freeze

Use when a feature should be captured as a compact AI retrieval index under `core/features/`.

Frozen feature files are for future AI code agents first. They help an agent quickly locate the relevant code for an existing feature without scanning the whole repository or spending tokens on unrelated files. Human readability matters mainly at the file-name level, so a person can also recognize the feature from a directory listing.

## When to Run

- After a successful merge, to record the feature for future AI-assisted development.
- Before updating or fixing an existing feature, when no useful frozen feature file exists.
- When an existing frozen feature file is missing important search terms, code paths, behavior names, or related feature links.
- When explicitly requested by the user.

## Retrieval Model

Assume the next AI agent will search in this order:

1. List or scan filenames under `core/features/` using commands like `find`, `rg --files`, `ls`, or shell globbing.
2. Pick likely feature files from filename keywords before reading any file contents.
3. Read only the selected frozen feature files.
4. Use the file paths, symbols, routes, commands, and keywords inside those files to locate source code with `rg`, `grep`, or IDE search.

The filename is therefore the first retrieval surface. The file content is the second retrieval surface. Both must contain stable, explicit keywords.

Do not design frozen feature files as human documentation. Design them as code-location metadata for AI agents.

## Steps

### Step 1: Identify the feature boundary

- Read the feature's `requirements.md`, `implementation.md`, `AGENTS.md`, `CHANGELOG.md`, and any already-loaded implementation context.
- Identify the smallest useful feature boundary for future updates.
- Prefer one frozen feature file per independently updateable feature.
- Split large behavior into multiple frozen feature files when future work would likely target only one sub-area.

### Step 2: Inspect only relevant project code

- Read the relevant source files, routes, components, tests, commands, configuration, schemas, prompts, workflows, and skill files.
- Do not scan the whole repository unless the feature cannot be located from existing lifecycle docs and targeted search.
- Check existing files in `core/features/` to avoid duplicates and identify related frozen features.
- Collect only retrieval-useful references:
  - project-root-relative file paths
  - directory paths
  - route paths and API endpoints
  - function, component, class, hook, command, workflow, skill, schema, table, or config names
  - user-facing labels and domain terms that an agent might search for
  - stable error messages, event names, environment variables, and CLI names

### Step 3: Choose a natural feature file name

Use `core/features/{natural-feature-phrase}.md`.

Filename rules:

- Use lowercase letters, numbers, and hyphens only.
- Name the file with the same clear English feature phrase developers would use during planning, implementation, review, and bug fixing.
- Prefer a descriptive feature phrase over a short generic filename, but do not stuff every possible keyword into the filename.
- Include the product area and main feature noun when they make the phrase clearer.
- Put extra synonyms, implementation terms, and alternate user phrasing in `Retrieval Keywords`, not in the filename.
- Avoid awkward keyword chains, clever abbreviations, internal-only shorthand, and vague names like `settings.md`, `workflow.md`, `ui.md`, or `agent.md`.
- Keep the filename understandable to both humans and AI agents.
- Rename outdated vague files when a clearer filename improves retrieval.

### Step 4: Write or update the frozen feature file

Use this structure:

```md
# Feature Retrieval Index: Short Human-Readable Name

## Retrieval Keywords

## Scope

## Main Behavior

## Code Map

## Search Commands

## Related Features

## Update Notes
```

Section rules:

- `Retrieval Keywords`: dense comma-separated keywords and synonyms. Include product terms, UI labels, route names, command names, file names, class/function names, and common user phrasing.
- `Scope`: two to five bullets defining what belongs in this feature and what does not.
- `Main Behavior`: compact bullets describing observable behavior and important system behavior.
- `Code Map`: project-root-relative paths plus nearby symbols or search terms. No line numbers.
- `Search Commands`: ready-to-run `rg` or `find` commands that quickly locate the implementation from the repository root.
- `Related Features`: links to other files under `core/features/` for adjacent behavior. Do not duplicate their detail.
- `Update Notes`: constraints, invariants, compatibility notes, data migrations, test commands, or risk areas future agents should preserve.

## Content Style

- Optimize for AI retrieval, not narrative explanation.
- Use compact bullets, tables, and keyword lists.
- Repeat important stable keywords when repetition improves searchability.
- Prefer exact code identifiers and exact user-visible labels over paraphrases.
- Include enough synonyms for likely future requests, for example `freeze`, `frozen`, `feature index`, `retrieval`, `locate code`, and `core/features`.
- Include common user phrasing and misspellings only when they are likely to appear in future requests.
- Do not include large code excerpts.
- Do not include line numbers, because they become stale quickly.
- Do not include broad repository summaries unrelated to the feature.
- If a frozen feature file grows too large, split it into narrower keyword-rich files and cross-link them in `Related Features`.

## Verification

- The file exists under `core/features/`.
- The filename is keyword-rich enough to be selected from a filename-only scan.
- The filename is still understandable to a human.
- The file content contains enough keywords for `rg`/`grep` retrieval.
- `Code Map` uses project-root-relative paths and stable symbols without line numbers.
- `Search Commands` work from the repository root.
- `Related Features` points to adjacent frozen feature files instead of duplicating their content.
- The file helps a future AI agent avoid scanning the whole codebase for this feature.
