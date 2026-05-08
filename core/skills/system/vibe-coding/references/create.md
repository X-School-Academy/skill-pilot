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
- `workspace/vibe-coding/{project-name}/design-docs/`
- `workspace/vibe-coding/{project-name}/design-docs/archive/`

### Step 3: Write the Requirement

Create `workspace/vibe-coding/{project-name}/design-docs/requirements.md` from the user's prompt in clear English. Keep it requirement-focused; avoid implementation details.

### Step 4: Report

Report the project folder path and `design-docs/requirements.md`.
