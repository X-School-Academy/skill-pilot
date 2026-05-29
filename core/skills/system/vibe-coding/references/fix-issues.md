# Stage Reference: fix-issues

Set up the trigger doc for a fix cycle. Planning and implementation follow as separate stages.

## When to Use

- The user wants bugs or issues fixed in an existing project
- Bug reports or issue notes have been collected

## Steps

### Step 1: Prepare the Trigger Doc

If `issues.md` already exists from a previous cycle, archive it first:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mkdir -p design-archive
mv issues.md "design-archive/issues.$timestamp.md"
```

If `issues.md` does not exist, create it from the user's bug descriptions or issue notes.

### Step 2: Report

Confirm `issues.md` is ready. State that the next step is `refine` → `initialize` → `plan` → `implement` → `test` → `review` → `merge`.
