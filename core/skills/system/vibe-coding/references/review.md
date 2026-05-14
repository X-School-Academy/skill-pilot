# Stage Reference: review

Review a Vibe Coding project implementation with a code-review mindset.

## When to Use

- The user asks to review the implementation
- `design-docs/implementation.md` exists
- Bugs, regressions, and missing tests should be identified

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implementation.md` and inspect the relevant code paths.

### Step 2: Review for Findings

Prioritize correctness issues, regressions, unsafe assumptions, and missing verification. Also check for code cleanliness, efficiency, and documentation quality.

### Step 3: Fix Issues Found

Fix all issues discovered during the review. After fixing, re-inspect the affected code to confirm the fix is correct and no new issues were introduced. Only proceed once the code is clean and all findings are resolved.

### Step 4: Save the Review

Write findings and their resolutions to `design-docs/reviewed.md` (created fresh per review). Record what was found, what was fixed, and any residual risks.

Update `design-docs/implementation.md` to reflect any code changes made during the review.

### Step 5: Hand off

Present the review summary to the user. Once the user has decided what to do with any remaining notes (or when running in the default flow, proceed directly to `deploy` or `merge`), the consuming stage is responsible for archiving `reviewed.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/reviewed.md "design-docs/archive/reviewed.$timestamp.md"
```

If the next stage is run in the same turn, do the archive at that point. Otherwise leave `reviewed.md` in place for human review.
