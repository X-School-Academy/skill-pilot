# Stage Reference: fix-issues

Fix issues defined in `design-docs/issues.md`.

## When to Use

- The user wants issues fixed from `issues.md`
- Bug reports or issue notes have been collected
- Work is bug fixing rather than feature planning

## Steps

### Step 1: Read the Issue File

Read `design-docs/issues.md` and inspect the affected code.

### Step 2: Plan the Fixes (for human review)

Write the planned fix approach to `design-docs/issues-plan.md`. Briefly summarize for the user.

### Step 3: Implement the Fixes

Apply targeted fixes for the reported problems.

### Step 4: Verify

Run the most relevant checks to confirm the issues are resolved.

### Step 5: Record the Fix Implementation

Write `design-docs/issues-impl.md` describing which issues were fixed, how they were verified, and any remaining follow-up. This is for human review.

### Step 6: Refresh Living Design Docs

Update `design-docs/requirements.md`, `design-docs/plan.md`, and `design-docs/implement.md` to reflect any behavior change introduced by the fixes.

### Step 7: Archive the Fix Cycle Files

After human review (or at the end of this turn if no review is requested):

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/issues.md      "design-docs/archive/issues.$timestamp.md"
mv design-docs/issues-plan.md "design-docs/archive/issues-plan.$timestamp.md"
mv design-docs/issues-impl.md "design-docs/archive/issues-impl.$timestamp.md"
```

### Step 8: Report

Report which issues were fixed, how they were verified, refreshed living docs, and archived files.
