# Explore, Sessions, and Worktrees

This folder stores the Explore showcase data, and it also defines the runtime assumptions that the WebUI uses when launching template-driven sessions.

## Core Idea

Skill Pilot can run in two WebUI/engine instances:

- `production`: stable operator UI and stable web terminal
- `development`: live-reloading UI used to monitor changes to `core/webui` and `core/engine`

The stable rule is:

- use the production WebUI terminal to do development work that may restart the dev server
- use the dev WebUI only to monitor the dev result

This avoids losing the active terminal when frontend/backend code reloads.

## New Session Worktree Behavior

When the repo has Git worktrees:

- the New Session UI should expose a worktree selector
- embedded New Session panels should expose the same selector
- selecting a worktree means the AI agent tmux session starts from that worktree directory
- template launches should redirect the current instance to a New Session URL that includes the chosen worktree path so the selector is prefilled

## File Manager Terminal Behavior

The file manager terminal should start from the selected folder root.

- if the user is inside a worktree root or a folder under a worktree, the terminal should start there
- switching from one worktree root to another should not silently reuse a terminal that is still attached to the old root

## Template Launch Behavior

Template launch must consider both the sample `in_mode` and the current instance runtime.

### Prod sample

- if a sample runs in `prod`, launching it should keep the user on the current instance
- if the sample also uses a worktree, pass that worktree path into the current-instance New Session URL

### Dev sample from dev instance

- keep the user in the current dev instance
- do not launch another dev instance
- do not use a worktree, even if the sample metadata requests one
- do not check out a sample git tag, even if the sample metadata requests one
- start the session from the current dev checkout only

### Dev sample from prod instance

- start or reuse the dev environment as needed
- do not move the working terminal into the dev WebUI
- first show a dev-instance link so the user can monitor the dev result
- then let the user continue in the current prod instance
- continuing should redirect the current prod instance to a New Session URL with the worktree path when applicable

This preserves a stable production web terminal while still allowing live monitoring in dev.

## Dev Runtime Restrictions

When the current WebUI runtime is `development`:

- `Using worktree` must be disabled in the template modal
- sample `use_worktree: true` must be ignored
- sample `git_tag` checkout must be ignored
- template launch must stay on the current dev checkout

This prevents the dev instance from trying to launch or manage a second dev runtime.

## Why This Exists

Editing `core/webui` or `core/engine` can restart the dev frontend/backend. If the active working terminal lives inside the dev WebUI, that terminal can be interrupted or lost. The safer workflow is:

1. work from the production WebUI terminal
2. target a worktree when needed
3. open the dev WebUI separately for live monitoring

For changes outside `core/webui` and `core/engine`, working directly in the dev instance is usually acceptable.
