# Feature Lifecycle: Freeze

Use when a feature should be captured as a compact, reusable reference under `core/features/`.

## When to Run

- After a successful merge, to record the feature for future AI-assisted development
- When an existing feature file is missing, outdated, or too vague
- When explicitly requested by the user

## Steps

### Step 1: Identify the feature to freeze

- Read the feature's `requirements.md` and any related implementation context already loaded.
- Identify the user-facing feature boundary. Prefer one feature per file.

### Step 2: Inspect the project

- Read the relevant source files, routes, and components to collect compact code references.
- Check existing files in `core/features/` to avoid duplicates and match naming patterns.
- Collect only:
  - project-root-relative file paths
  - function, component, route, class, or keyword names useful for `rg`/`grep`

### Step 3: Choose the target file name

- Use lowercase letters and hyphens only (e.g. `my-feature.md`).
- Use `feature-name--sub-feature-name.md` only when the behavior is large enough to split.

### Step 4: Write or update `core/features/{feature-name}.md`

Include these sections:

```
# Feature Name
## Brief
## User Value
## Main Behavior
## Related Features
## Code References
```

Content rules:

- `Brief`: one or two sentences, understandable by a non-technical user.
- `Main Behavior`: compact bullets describing observable behavior.
- `Related Features`: required when adjacent flows, dependencies, or companion screens exist — point to other feature files instead of copying their detail.
- `Code References`: file paths, function/component/route names, and search keywords only. No line numbers. No large code excerpts.

### Step 5: Optimize for AI retrieval

- Remove filler text and repeated statements.
- Prefer stable search terms over prose-heavy explanations.
- If the file is too large, split into sub-feature files.

### Step 6: Verify

- File is under `core/features/`.
- File name is lowercase with hyphens only.
- Feature is described at user level unless truly technical-only.
- `Related Features` references adjacent behavior instead of duplicating it.
- `Code References` has no line numbers and no oversized sections.
