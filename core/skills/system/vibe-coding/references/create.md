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
- `workspace/vibe-coding/{project-name}/assets/`
- `workspace/vibe-coding/{project-name}/design-docs/`
- `workspace/vibe-coding/{project-name}/design-docs/archive/`

### Step 3: Create Dashboard Assets

Create `workspace/vibe-coding/{project-name}/assets/info.yaml`:

```yaml
display_name: Project Display Name
commands:
  start: ""
  dev: ""
  build: ""
  stop: ""
```

Use a clear display name derived from the project request. Fill in command values only when the project stack is already known and the command is safe to run from the project root.

Use the `create-image` skill to create `workspace/vibe-coding/{project-name}/assets/icon.png` as a square project icon. The icon should communicate the product concept and remain legible at small dashboard sizes. If image generation is blocked, leave a short note in the report and keep the project usable without the icon.

### Step 4: Write the Requirement

Create `workspace/vibe-coding/{project-name}/design-docs/requirements.md` from the user's prompt in clear English. Keep it requirement-focused; avoid implementation details.

### Step 5: Report

Report the project folder path, `assets/info.yaml`, `assets/icon.png` if created, and `design-docs/requirements.md`.
