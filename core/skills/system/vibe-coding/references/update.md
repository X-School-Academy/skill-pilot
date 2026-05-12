# Stage Reference: update

Apply changes from `design-docs/update.md` to an existing project.

## When to Use

- The user wants changes applied from `update.md`
- The project already exists and needs iteration
- The task is an update rather than net-new implementation

## Steps

### Step 1: Read the Update Request

Read `design-docs/update.md` and inspect the relevant code paths.

### Step 2: Plan the Update (for human review)

Write the planned approach to `design-docs/update-plan.md`. Briefly summarize for the user.

### Step 3: Implement the Update

Apply the requested changes with minimal unrelated modifications.

### Step 4: Verify

Run the most relevant targeted checks for the changed behavior.

### Step 5: Record the Update Implementation

Write `design-docs/update-impl.md` describing what changed, what was verified, and any risks. This is for human review.

### Step 6: Refresh Living Design Docs

Update `design-docs/requirements.md`, `design-docs/plan.md`, and `design-docs/implementation.md` to reflect the changes from this update cycle.

Update `CHANGELOG.md` with a summary of what changed in this update cycle (a final changelog entry will also be added by the `merge` stage).

### Step 7: Archive the Update Cycle Files

After human review (or at the end of this turn if no review is requested):

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/update.md      "design-docs/archive/update.$timestamp.md"
mv design-docs/update-plan.md "design-docs/archive/update-plan.$timestamp.md"
mv design-docs/update-impl.md "design-docs/archive/update-impl.$timestamp.md"
```

### Step 8: Report

Report the updated behavior, verification, refreshed living docs, and archived files. State that the next step is `test`, then `review`, then `merge`.
