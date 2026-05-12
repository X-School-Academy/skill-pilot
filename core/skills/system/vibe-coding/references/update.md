# Stage Reference: update

Set up the trigger doc for an update cycle. Planning and implementation follow as separate stages.

## When to Use

- The user wants to apply changes to an existing project
- The project already exists and needs iteration

## Steps

### Step 1: Prepare the Trigger Doc

If `design-docs/update.md` already exists from a previous cycle, archive it first:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/update.md "design-docs/archive/update.$timestamp.md"
```

If `design-docs/update.md` does not exist, create it from the user's description of the requested changes.

### Step 2: Report

Confirm `update.md` is ready. State that the next step is `refine` → `initialize` → `plan` → `implement` → `test` → `review` → `merge`.
