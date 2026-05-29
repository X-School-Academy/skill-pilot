# Stage Reference: merge

Merge the update or bug fix branch back to the main branch after review passes.

## When to Use

- The update or bug fix has passed the `review` stage
- The working branch needs to be merged back to main
- Used in the update or bug fix flow: `... → review → merge → deploy`

## Steps

### Step 1: Confirm Review Passed

Verify that the `review` stage completed without unresolved findings. If `reviewed.md` still has open issues, resolve them before merging.

### Step 2: Merge the Branch

Use the `git-github` skill to merge the branch back to the main branch. Prefer a squash merge or a regular merge depending on the project's conventions. Confirm the merge succeeded before continuing.

### Step 3: Update CHANGELOG.md

Append a new versioned entry to `CHANGELOG.md` describing what changed in this update or fix cycle. Include:

- A short summary of the change
- The date of the merge
- The branch name that was merged

### Step 4: Refresh Living Design Docs

Update the living design docs to reflect the merged state:

- `requirements.md` — if scope changed
- `implementation.md` — to reflect the merged implementation
- `deployment.md` — if deployment configuration changed

### Step 5: Archive the Consumed Intermediate Files

Archive `reviewed.md` if it has not already been archived:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mkdir -p design-archive
mv reviewed.md "design-archive/reviewed.$timestamp.md"
```

### Step 6: Report

Confirm the branch was merged, the `CHANGELOG.md` was updated, and which living docs were refreshed. State the next step (`deploy` if a new deployment is needed).
