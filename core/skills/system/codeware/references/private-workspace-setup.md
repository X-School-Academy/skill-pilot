# Create Private Workspace Repo

Replace the sample `workspace/` submodule (`https://github.com/X-School-Academy/skill-pilot_workspace.git`) with a new empty private GitHub repository owned by the user. This reference mirrors the steps in `workspace/README.md` and adds safety checks an AI agent must run.

## When to use

Run this flow when:
- The current `workspace/` `origin` still points to `https://github.com/X-School-Academy/skill-pilot_workspace.git`, and
- The user wants their work version-controlled under their own private repo.

If `origin` already points to a non-sample URL, stop and report the current URL instead of proceeding; the workspace has already been linked.

## Role announcements

Announce each step before running it, for example:
- **As a DevOps Engineer**, I will check the current `workspace/` remote.
- **As a Security Engineer**, I will warn about browser automation risks before opening github.com.

## Step 1: Verify the current state

From the Skill Pilot repo root:

```bash
cd workspace
git remote -v
git status --porcelain
```

Stop and ask the user how to proceed if any of the following is true:
- `origin` is not `https://github.com/X-School-Academy/skill-pilot_workspace.git` because it is already personalized.
- `git status` shows uncommitted changes inside `workspace/`; commit or stash them first so they are preserved when the remote changes.

## Step 2: Have the user create an empty private repo

Ask the user to create a new empty private GitHub repository with no README, license, or `.gitignore`, for example:

```text
https://github.com/<you>/my-workspace.git
```

If the user wants you to open a browser to create it, first warn about prompt-injection risk on third-party websites and confirm `github.com` is trusted before using any browser-automation tool.

Collect the exact HTTPS URL of the new repo from the user. Do not guess the URL.

## Step 3: Point `workspace/` origin at the new repo and push

From inside the `workspace/` folder:

```bash
cd workspace
git remote set-url origin https://github.com/<you>/my-workspace.git
git push -u origin main
```

If the user's local workspace branch is not `main`, push the actual current branch name instead and record it in the report.

## Step 4: Update the parent repo's submodule URL

From the Skill Pilot repo root:

```bash
git config -f .gitmodules submodule.workspace.url https://github.com/<you>/my-workspace.git
git submodule sync
git add .gitmodules
git commit -m "chore: point workspace submodule to personal private repo"
```

Do not push this commit automatically. Report that the `.gitmodules` commit is ready locally, and ask whether to push it now.

## Step 5: Verify

Run, and show the user:

```bash
cd workspace && git remote -v
cd .. && git submodule status
```

Confirm `origin` is the new private URL and that the submodule commit is pointing at the pushed workspace commit.

## Report

Return:
- Old and new `workspace/` remote URLs
- The workspace branch that was pushed
- Whether the `.gitmodules` change was committed, and whether it was pushed
- Any blocker encountered
