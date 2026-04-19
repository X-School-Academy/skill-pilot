# Coreware page — Original request summary

This document captures what the user asked for so that future work, reviews, or handoffs can reference the exact scope.

## Reference material the user pointed to

- `about/` — source of version / build info
- `core/skills/system/codeware-management/` — the agent skill that this new page drives
- `workspace/` (and specifically `workspace/README.md`) — authoritative steps for replacing the sample submodule with a private repo

## New page

Create a new page **`/coreware`** in `core/webui`, placed **under the Skill Pilot section** of the sidebar (next to the existing `Development` entry).

The page uses a **tab menu** with four tabs: **About**, **Codeware**, **Workspace**, **Worktree**.

## Tab 1 — About

Show the current Skill Pilot agent version info read from `about/version.json5` (version + build).

## Tab 2 — Codeware

Four buttons, each opens the same bottom "new session" panel (the same embedded session UI the Development page uses) pre-filled with a prompt template routed to the `codeware-management` agent skill:

- **Update** — prompt template like: _"use codeware-management agent skill to check and update codeware"_
- **Restore** — prompt template for the `restore` operation
- **Link to my Repos** — prompt template for the `add remote` operation
- **Contribute** — prompt template like: _"use codeware-management agent skill to contribute what is feature or bug fix you have made etc"_

> Clarification: **Link to my Repos** and **Contribute** are two separate buttons.

## Tab 3 — Workspace

First, **extend `core/skills/system/codeware-management`** to add a new operation:

- **create private workspace repo** — the skill's reference material must be grounded in `workspace/README.md`, which already documents how to create and link the user's private repo.

Then, on the Workspace tab:

- If the current `workspace/` origin is still `https://github.com/X-School-Academy/skill-pilot_workspace.git` (the sample), show a **Create Private Workspace Repo** button. Clicking it opens the bottom new-session panel with a prompt template that invokes the updated `codeware-management` skill.
- If the workspace origin is already a personal remote, no action is needed.

## Tab 4 — Worktree

- **List all worktrees** currently registered with the repo.
- Each non-main worktree has a **Remove** button.
- A **Create Worktree** button lets the user enter a name:
  - First check if the target worktree folder already exists. If it does, fail rather than overwrite.
  - Otherwise create the new worktree.

### Follow the existing Explore worktree logic

- Reuse the same folder-location convention already used by Explore: worktrees live at `../{current_folder_name}_{worktree_name}` (sibling to the main repo).
- **Refactor and share the worktree code** between Explore and Coreware so both paths call the same helpers. Keep the code clean rather than duplicating it.

## Delivery constraints

- Match the existing Skill Pilot UI patterns in `core/webui` (Mantine, EmbeddedSessionPanel, etc.).
- Announce active role(s) before acting, per the project's `CLAUDE.md`.
- Get user approval before committing code or making major changes.
