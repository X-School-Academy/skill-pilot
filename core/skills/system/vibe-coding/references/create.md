# Stage Reference: create

Bootstrap a new Vibe Coding project from the user's prompt.

## When to Use

- The user wants to start a new project from a short prompt
- The project folder does not yet exist or has no `requirements.md`

## Steps

### Step 1: Determine the Project Name

Derive a concise kebab-case project name from the user's request if none is provided.

### Step 2: Create the Project Layout

Create:

- `workspace/vibe-coding/{project-name}/`

Do not create `design-archive/` during project creation. Archive stages create it only when they need to move an older design file.

### Step 3: Write the Requirement

Create `workspace/vibe-coding/{project-name}/requirements.md` from the user's prompt in clear English. Keep it requirement-focused; avoid implementation details.

### Step 4: Create Top-Level Project Files

Create stub versions of the three top-level project files:

- `README.md` — project name as the H1 heading, one-line description derived from the requirements, placeholder sections for Overview, Usage, and Setup.
- `CHANGELOG.md` — single `## Unreleased` section with no entries yet.
- `AGENTS.md` — use `references/agents-template.md` as the template; replace `{Project Name}` and `{project-name}` with the actual project name.

### Step 5: Report

Report the project folder path, `requirements.md`, and the three top-level files created.
