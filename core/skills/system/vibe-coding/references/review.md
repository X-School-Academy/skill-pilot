# Stage Reference: review

Review a Vibe Coding project implementation with a code-review mindset.

## When to Use

- The user asks to review the implementation
- `design-docs/implement.md` exists
- Bugs, regressions, and missing tests should be identified

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implement.md` and inspect the relevant code paths.

### Step 2: Review for Findings

Prioritize correctness issues, regressions, unsafe assumptions, and missing verification.

### Step 3: Save the Review

Write findings to `design-docs/reviewed.md` (created fresh per review). Order findings by severity, then list open questions and residual risks.

### Step 4: Hand off

Present the findings to the user. Once the user has decided what to do with them (typically by writing `issues.md` or `update.md`), the consuming stage is responsible for archiving `reviewed.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/reviewed.md "design-docs/archive/reviewed.$timestamp.md"
```

If the next stage is run in the same turn, do the archive at that point. Otherwise leave `reviewed.md` in place for human review.
