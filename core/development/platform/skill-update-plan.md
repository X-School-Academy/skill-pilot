# Update Plan: Skill Pilot Feature Skills

## Overview

Update `skill-pilot-feature-*` agent skills to improve branching guidance, merge workflow, and feature-file awareness.

---

## Change 1: Branching in `skill-pilot-feature-initial`

**Problem:** The skill says "create a new branch" but doesn't distinguish between new feature, update, or bug fix scenarios on the user branch.

**Changes:** Update Step 2 to clarify branching strategy:

- For a new feature: create a branch named `feature/{feature-name}` from the user branch.
- For an update (driven by `update.md`): create a branch named `update/{feature-name}` from the user branch.
- For a bug fix (driven by `issues.md`): create a branch named `fix/{feature-name}` from the user branch.

Only create these branches when current is on the user branch, and no code is not committed, or need to ask to confirm it, or commit auto/switch to user branch first

once create the new branch, then switch to the new branch and working on the new branch

The skill should detect the trigger context (new requirement vs update.md vs issues.md) and choose the branch prefix accordingly.

**File to modify:**
- `core/skills/system/skill-pilot-feature-initial/SKILL.md`

---

## Change 2: Merge Workflow in `skill-pilot-feature-merge`

**Problem:** The merge skill doesn't mention freezing the feature after merge.

**Changes:** Update the instructions to:

1. Merge the feature branch back to the user branch.
2. After a successful merge, use agent skill `skill-pilot-freeze-core-feature` to freeze the feature into `core/features/`.
3. Clean up the feature branch after merge.

**File to modify:**
- `core/skills/system/skill-pilot-feature-merge/SKILL.md`

---

## Change 3: Feature File References (All 10 Skills)

**Problem:** None of the `skill-pilot-feature-*` skills reference `core/features/*.md` for context, so the agent doesn't know about related frozen feature docs.

**Changes:** Add a "Feature Context" section (before `## Instructions`) to all 10 skills:

> ## Feature Context
>
> The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`.

This tells the agent to look at feature references in the requirement but avoids loading every feature file.

If the same file has loaded, and not load it again, unless the file updated or asked by user to read again

**Files to modify (all under `core/skills/system/`):**
- `skill-pilot-feature-create/SKILL.md`
- `skill-pilot-feature-refine/SKILL.md`
- `skill-pilot-feature-initial/SKILL.md`
- `skill-pilot-feature-plan/SKILL.md`
- `skill-pilot-feature-implement/SKILL.md`
- `skill-pilot-feature-review/SKILL.md`
- `skill-pilot-feature-test/SKILL.md`
- `skill-pilot-feature-merge/SKILL.md`
- `skill-pilot-feature-update/SKILL.md`
- `skill-pilot-feature-fix-issues/SKILL.md`

---

## Implementation Order

1. Change 3 - Feature context section (all 10 skills)
2. Change 1 - Branching strategy (initial skill)
3. Change 2 - Merge + freeze workflow (merge skill)

## Verification

- Read each modified SKILL.md to confirm content is correct
- Confirm no skill references `core/features/` with a wildcard glob — only mentioned files
