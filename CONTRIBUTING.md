# Contributing to Skill Pilot

Thank you for contributing to **Skill Pilot**.

This guide explains the recommended Git workflow for users who:

1. install Skill Pilot from the official install script
2. develop locally on their own branch
3. fork the repo to their own GitHub account for backup
4. create a clean pull request to the `contrib` branch

---

# Repo branches

This repository currently uses:

- `codeware` — default branch
- `contrib` — contribution target branch

Important:

- The install script starts users from the default `codeware` branch.
- For a **clean contribution pull request**, create a new feature branch from `upstream/contrib`.

---

# 1. Install Skill Pilot

Users can install Skill Pilot with:

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
````

This will run commands similar to:

```bash
git clone https://github.com/X-School-Academy/skill-pilot
cd skill-pilot
git checkout -b user
```

At this point:

* the local repo was cloned from the official repo
* the current branch is `user`
* the `user` branch was created from the default branch `codeware`

Check the current branch:

```bash
git branch
```

Check remotes:

```bash
git remote -v
```

Normally right after clone, the official repo is the `origin` remote.

---

# 2. Develop on the `user` branch

Users can make local changes on the `user` branch:

```bash
git status
git add .
git commit -m "My local changes"
```

Useful commands:

```bash
git branch
git status
git log --oneline --decorate --graph -n 10
```

---

# 3. Fork the repo and connect the personal GitHub remote

After local development starts, the user can fork the repo on GitHub.

Open:

```text
https://github.com/X-School-Academy/skill-pilot
```

Click **Fork**.

Recommended fork option:

* fork the default branch (`codeware`) only

This creates a fork like:

```text
https://github.com/<your-github-user>/skill-pilot
```

## Update local remotes

Because the local clone originally came from the official repo, `origin` usually points to the official repo.

We recommend renaming that remote to `upstream`, then adding the user's fork as `origin`.

```bash
git remote rename origin upstream
git remote add origin https://github.com/<your-github-user>/skill-pilot.git
```

Check remotes again:

```bash
git remote -v
```

Expected result:

```bash
origin    https://github.com/<your-github-user>/skill-pilot.git (fetch)
origin    https://github.com/<your-github-user>/skill-pilot.git (push)
upstream  https://github.com/X-School-Academy/skill-pilot.git (fetch)
upstream  https://github.com/X-School-Academy/skill-pilot.git (push)
```

## Push the `user` branch to the personal fork

This is useful for saving work to GitHub:

```bash
git checkout user
git push -u origin user
```

What `-u` means:

* `-u` means `--set-upstream`
* it tells Git to track `origin/user` for the local `user` branch

After that, while on `user`, these usually work:

```bash
git push
git pull
```

Check tracking info:

```bash
git branch -vv
```

---

# 4. Create a clean contribution branch from `contrib`

When ready to contribute code back to the official repository, do **not** use the `user` branch directly for the pull request targetting `contrib`.

Instead:

1. fetch the latest official branches
2. create a new feature branch from `upstream/contrib`
3. move or re-apply your contribution onto that feature branch
4. push the feature branch to your fork
5. open a pull request from your fork to `X-School-Academy/skill-pilot:contrib`

## Fetch latest official branches

```bash
git fetch upstream
```

Check remote branches:

```bash
git branch -r
```

You should see something like:

```bash
origin/user
upstream/codeware
upstream/contrib
```

## Create a contribution feature branch

Example:

```bash
git checkout -b my-feature upstream/contrib
```

This creates a new local branch based on the official `contrib` branch.

---

# 5. Bring your changes into the contribution branch

There are several ways to do this.

## Option A: manually re-apply the changes

If the change is small, you can copy the files or re-edit them, then commit:

```bash
git add .
git commit -m "Add my contribution"
```

## Option B: cherry-pick commits from `user`

If the work on `user` is already committed and clean, you can cherry-pick those commits.

First inspect commits:

```bash
git log --oneline user
```

Then cherry-pick selected commits:

```bash
git cherry-pick <commit-id>
```

Example:

```bash
git cherry-pick abc1234
```

If needed, cherry-pick multiple commits:

```bash
git cherry-pick <commit1> <commit2> <commit3>
```

This is often the cleanest way.

---

# 6. Push the contribution branch to the personal fork

Push the feature branch to the user's fork:

```bash
git push -u origin my-feature
```

After that, the local branch tracks the remote fork branch.

Check tracking:

```bash
git branch -vv
```

---

# 7. Open a pull request to the official `contrib` branch

On GitHub, open the user's fork:

```text
https://github.com/<your-github-user>/skill-pilot
```

Then create a pull request with:

* **base repository**: `X-School-Academy/skill-pilot`
* **base branch**: `contrib`
* **head repository**: `<your-github-user>/skill-pilot`
* **compare branch**: `my-feature`

Then submit the pull request.

Important:

* base must be `contrib`
* head branch should be your clean feature branch created from `upstream/contrib`

---

# Common Git commands

## Check current branch

```bash
git branch
```

## Check current status

```bash
git status
```

## See remotes

```bash
git remote -v
```

## See local branches and tracked remote branches

```bash
git branch -vv
```

## See remote branches

```bash
git branch -r
```

## Fetch latest data from a remote

```bash
git fetch origin
git fetch upstream
```

## Create a new branch

```bash
git checkout -b my-branch
```

## Create a branch from a specific remote branch

```bash
git checkout -b my-branch upstream/contrib
```

## Add and commit changes

```bash
git add .
git commit -m "My change"
```

## Push branch to remote and set upstream

```bash
git push -u origin my-branch
```

## Pull from the tracked remote branch

```bash
git pull
```

## Pull from a specific remote branch explicitly

```bash
git pull upstream contrib
git pull upstream codeware
```

## Merge a remote branch into the current branch

```bash
git fetch upstream
git merge upstream/contrib
```

## Rebase current branch onto a remote branch

```bash
git fetch upstream
git rebase upstream/contrib
```

## Show commit history

```bash
git log --oneline --decorate --graph -n 20
```

## Cherry-pick a commit

```bash
git cherry-pick <commit-id>
```

---

# Understanding `origin` and `upstream`

In this guide:

* `upstream` = the official Skill Pilot repo
* `origin` = the user's personal fork

Recommended setup:

```bash
origin    -> https://github.com/<your-github-user>/skill-pilot.git
upstream  -> https://github.com/X-School-Academy/skill-pilot.git
```

This makes the workflow much easier to understand:

* pull official updates from `upstream`
* push personal work to `origin`

---

# How to check which branch tracks which remote

Use:

```bash
git branch -vv
```

Example:

```bash
* user              abc1234 [origin/user] local work
  my-feature def5678 [origin/my-feature] add docs
  codeware          123abcd [upstream/codeware] sync official
```

This means:

* local `user` tracks `origin/user`
* local `my-feature` tracks `origin/my-feature`
* local `codeware` tracks `upstream/codeware`

To check one branch directly:

```bash
git config --get branch.user.remote
git config --get branch.user.merge
```

---

# Set a branch tracking remote without pushing

If the remote branch already exists, you can set tracking manually:

```bash
git branch --set-upstream-to=origin/user user
```

Example:

```bash
git branch --set-upstream-to=upstream/codeware codeware
```

Check it:

```bash
git branch -vv
```

---

# Troubleshooting

## I fetched from `orgin` by mistake

If you created a typo remote named `orgin`, Git will store remote branches under `orgin/...`, not `origin/...`.

Check remotes:

```bash
git remote -v
```

Rename it:

```bash
git remote rename orgin origin
```

Then fetch again:

```bash
git fetch origin
```

## `fatal: the requested upstream branch 'origin/codeware' does not exist`

Usually one of these is true:

1. the remote name is wrong, such as `orgin` instead of `origin`
2. the remote branch was not fetched yet
3. the remote branch does not exist

Check:

```bash
git remote -v
git branch -r
```

Then use the correct remote-tracking branch name.

## My pull request contains too many unrelated changes

This usually means the branch was created from `codeware` but the PR targets `contrib`.

Fix:

1. fetch official repo
2. create a new feature branch from `upstream/contrib`
3. cherry-pick only the needed commits
4. push that clean branch
5. open the PR again

Example:

```bash
git fetch upstream
git checkout -b my-feature-clean upstream/contrib
git cherry-pick <commit-id>
git push -u origin my-feature-clean
```

---

# Recommended daily workflow

## First-time setup

```bash
curl -fsSL https://skill-pilot.ai/install.sh | bash
cd skill-pilot

git remote rename origin upstream
git remote add origin https://github.com/<your-github-user>/skill-pilot.git

git checkout user
git push -u origin user
```

## Keep saving personal work

```bash
git checkout user
git add .
git commit -m "Update local work"
git push
```

## Prepare a contribution branch

```bash
git fetch upstream
git checkout -b my-feature upstream/contrib
git cherry-pick <commit-id>
git push -u origin my-feature
```

Then open a pull request from:

```text
<your-github-user>/skill-pilot:my-feature
```

to:

```text
X-School-Academy/skill-pilot:contrib
```

---

# Summary

* install starts from `codeware`
* local development can happen on `user`
* fork to personal GitHub for backup
* rename official repo remote to `upstream`
* add personal fork as `origin`
* push `user` to personal fork for saving work
* for contribution, create a clean feature branch from `upstream/contrib`
* push that feature branch to personal fork
* open pull request to the official `contrib` branch
