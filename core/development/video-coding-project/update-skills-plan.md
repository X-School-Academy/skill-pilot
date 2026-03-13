# Update Plan: Vibe Coding Project Skills

## Overview

Update all `vibe-coding-project-*` agent skills and the WebUI to improve project isolation, git management, deployment guidance, file naming, and stage-file lifecycle.

---

## Change 1: Project Isolation Boundary (All Skills)

**Problem:** Skills don't instruct the AI agent to stay within the project folder.

**Changes:** Add a "Project Boundary" section to every `vibe-coding-project-*` SKILL.md (12 skills total) with this rule:

> **Project Boundary:** The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

**Files to modify:**
- `core/skills/system/vibe-coding-project-create/SKILL.md`
- `core/skills/system/vibe-coding-project-refine/SKILL.md`
- `core/skills/system/vibe-coding-project-brainstorm/SKILL.md`
- `core/skills/system/vibe-coding-project-initial/SKILL.md`
- `core/skills/system/vibe-coding-project-plan/SKILL.md`
- `core/skills/system/vibe-coding-project-implement/SKILL.md`
- `core/skills/system/vibe-coding-project-review/SKILL.md`
- `core/skills/system/vibe-coding-project-test/SKILL.md`
- `core/skills/system/vibe-coding-project-deploy/SKILL.md`
- `core/skills/system/vibe-coding-project-update/SKILL.md`
- `core/skills/system/vibe-coding-project-fix-issues/SKILL.md`
- `core/skills/system/vibe-coding-project-apply-brainstorm/SKILL.md`

---

## Change 2: Git Management in `vibe-coding-project-initial`

**Problem:** The initial skill doesn't ask the user how to manage git for the project.

**Changes:** Update Step 3 (Initialize Version Control) to:

1. Ask the user how they want to manage the project's code with git. The default is to use the Skill Pilot root project repository (no separate repo).
2. If the user provides an existing git URL:
   - Clone and merge the repo into the project folder.
   - Set it up as a git submodule of the root project.
3. If the user asks to create a new GitHub repo:
   - Use agent skill `playwright-cli` to create the repo from the GitHub website.
   - Then add it as a git submodule of the root project.

**File to modify:**
- `core/skills/system/vibe-coding-project-initial/SKILL.md`

---

## Change 3: Deployment Prompt in `vibe-coding-project-deploy`

**Problem:** The deploy skill assumes AWS EC2 without asking the user for their preferred deployment method.

**Changes:** Add a new step before "Deploy Safely":

> If no deployment target is specified in `requirements.md`, `plan.md`, or `implement.md`, ask the user how and where they want to deploy to production before proceeding.

Also soften the AWS EC2 default language to make it one option rather than the assumed default.

**File to modify:**
- `core/skills/system/vibe-coding-project-deploy/SKILL.md`

---

## Change 4: WebUI Action Button Prompts Include Project Name

**Problem:** Action button prompts don't include the project name, making them less clear in the new session.

**Changes:** Update `skillPromptSuffix` for every action in `fileActions` to include `Vibe coding project name: {project-name}` in the prompt.

Modify the prompt construction in `runAction` for skill mode from:
```
Use agent skill ${target} ${pendingAction.skillPromptSuffix}
```
to:
```
Use agent skill ${target} ${pendingAction.skillPromptSuffix}. Vibe coding project name: ${currentProject}
```

This is simpler than changing every individual suffix and keeps the project name consistently appended.

**File to modify:**
- `core/webui/pages/vibe-coding/index.tsx` (line ~420)

---

## Change 5: Brainstorm File Location in `vibe-coding-project-brainstorm`

**Problem:** The skill doesn't explicitly say the brainstorm file should be saved at the same location as the requirements file.

**Changes:** Update Step 3 to explicitly say:

> Save the brainstorm as `brainstorm.md` in the same project directory as `requirements.md` (i.e., `workspace/vibe-coding/{project-name}/brainstorm.md`). Create the file if it doesn't exist, or update it if it does.

**File to modify:**
- `core/skills/system/vibe-coding-project-brainstorm/SKILL.md`

---

## Change 6: Stage File Sync for Update and Fix-Issues Skills

**Problem:** After applying updates or fixing issues, the `requirements.md`, `plan.md`, and `implement.md` files are not updated to reflect the latest code state. Also, update/issues-driven plan and implement should use separate stage files.

**Changes for `vibe-coding-project-update`:**

Add a new step after "Verify the Update":

> **Step 4: Sync Stage Files**
> 1. Update `requirements.md`, `plan.md`, and `implement.md` to reflect any changes made by this update.
> 2. If the update was driven by `update.md`, create `update-plan.md` and `update-impl.md` as the plan and implementation records specific to this update cycle.
> 3. Note: `update.md`, `update-plan.md`, and `update-impl.md` are temporary files that the user may remove after review.

Renumber the existing "Summarize What Changed" step.

**Changes for `vibe-coding-project-fix-issues`:**

Add a new step after "Verify the Fixes":

> **Step 4: Sync Stage Files**
> 1. Update `requirements.md`, `plan.md`, and `implement.md` to reflect any changes made by the fixes.
> 2. If the fixes were driven by `issues.md`, create `issues-plan.md` and `issues-impl.md` as the plan and implementation records specific to this fix cycle.
> 3. Note: `issues.md`, `issues-plan.md`, and `issues-impl.md` are temporary files that the user may remove after review.

Renumber the existing "Summarize the Result" step.

**Files to modify:**
- `core/skills/system/vibe-coding-project-update/SKILL.md`
- `core/skills/system/vibe-coding-project-fix-issues/SKILL.md`

---

## Implementation Order

1. Change 1 - Project isolation (all 12 skills)
2. Change 2 - Git management (initial skill)
3. Change 3 - Deploy prompt (deploy skill)
4. Change 5 - Brainstorm file location (brainstorm skill)
5. Change 6 - Stage file sync (update + fix-issues skills)
6. Change 4 - WebUI prompt update (index.tsx)

## Package management tools

`uv` for python, and `pnpm` for nodejs unless user ask to user different tool (add to plan skill)

## Verification

- Read each modified SKILL.md to confirm content is correct
- Check WebUI builds without errors (`pnpm build` in core/webui)
- Manual test: click action buttons and verify prompts include project name
