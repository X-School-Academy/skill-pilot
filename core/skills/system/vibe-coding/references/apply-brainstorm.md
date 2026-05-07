# Stage Reference: apply-brainstorm

Merge selected ideas from `design-docs/brainstorm.md` into `design-docs/requirements.md`.

## When to Use

- `design-docs/brainstorm.md` exists with ideas to incorporate
- The user wants requirements updated based on brainstorm output

## Steps

### Step 1: Read Both Files

Read `design-docs/brainstorm.md` and `design-docs/requirements.md`.

### Step 2: Confirm Selection

Summarize the brainstorm ideas and ask which to apply, unless the user has already specified.

### Step 3: Merge Selected Ideas

Integrate selected ideas into `design-docs/requirements.md`:

- Preserve existing structure and intent
- Add new ideas in the right sections (features, scope, constraints, etc.)
- Avoid duplicating content already present
- Keep language consistent with the existing requirement style

### Step 4: Archive the Brainstorm

After applying, archive `brainstorm.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/brainstorm.md "design-docs/archive/brainstorm.$timestamp.md"
```

### Step 5: Report

Summarize what was added or changed in `requirements.md` and which brainstorm file was archived.
