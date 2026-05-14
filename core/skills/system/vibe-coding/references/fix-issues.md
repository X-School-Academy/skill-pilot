# Stage Reference: fix-issues

Set up the trigger doc for a fix cycle. Planning and implementation follow as separate stages.

## When to Use

- The user wants bugs or issues fixed in an existing project
- Bug reports or issue notes have been collected

## Steps

### Step 1: Prepare the Trigger Doc

If `design-docs/issues.md` already exists from a previous cycle, archive it first:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/issues.md "design-docs/archive/issues.$timestamp.md"
```

If `design-docs/issues.md` does not exist, create it from the user's bug descriptions or issue notes.

### Step 2: Report

Confirm `issues.md` is ready. State that the next step is `refine` → `initialize` → `plan` → `implement` → `test` → `review` → `merge`.
