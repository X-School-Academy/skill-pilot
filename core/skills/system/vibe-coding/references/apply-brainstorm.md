# Stage Reference: apply-brainstorm

Merge selected ideas from `brainstorm.md` into `requirements.md`.

## When to Use

- `brainstorm.md` exists with ideas to incorporate
- The user wants requirements updated based on brainstorm output

## Steps

### Step 1: Read Both Files

Read `brainstorm.md` and `requirements.md`.

### Step 2: Confirm Selection

Summarize the brainstorm ideas and ask which to apply, unless the user has already specified.

### Step 3: Merge Selected Ideas

Integrate selected ideas into `requirements.md`:

- Preserve existing structure and intent
- Add new ideas in the right sections (features, scope, constraints, etc.)
- Avoid duplicating content already present
- Keep language consistent with the existing requirement style

### Step 4: Archive the Brainstorm

After applying, archive `brainstorm.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mkdir -p design-archive
mv brainstorm.md "design-archive/brainstorm.$timestamp.md"
```

### Step 5: Report

Summarize what was added or changed in `requirements.md` and which brainstorm file was archived.
