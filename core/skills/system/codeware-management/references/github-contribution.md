# GitHub Remote and Contribution Flow

Use these procedures for `add remote` and `contribute`.

Official upstream repository:

- `https://github.com/X-School-Academy/skill-pilot.git`

## Add remote flow

Goal: ensure the official repo is `upstream` and the user's fork is `origin`.

### Option A: user provides a Git URL

1. Inspect current remotes:

```bash
git remote -v
```

2. If `origin` points to the official repo, rename it:

```bash
git remote rename origin upstream
```

3. If `upstream` does not exist, add it:

```bash
git remote add upstream https://github.com/X-School-Academy/skill-pilot.git
```

4. Add or update the user's fork remote as `origin`:

```bash
git remote add origin <user-fork-url>
```

If `origin` already exists and should be changed:

```bash
git remote set-url origin <user-fork-url>
```

5. Verify the result:

```bash
git remote -v
```

### Option B: fork from GitHub with browser automation

Before opening GitHub, warn the user that remote websites can contain prompt injection and confirm that `github.com` is trusted.

Then use the browser agent skill to:

1. Open `https://github.com/X-School-Academy/skill-pilot`
2. Click `Fork`
3. Complete the fork into the user's account
4. Copy the resulting fork URL

After the fork exists, apply Option A locally.

## Contribute flow

Goal: create a clean feature branch from `upstream/contrib`, push it to the user's fork, and open a pull request.

### Preconditions

- `origin` must exist and must be the user's fork, not the official repo
- `upstream` must point to `https://github.com/X-School-Academy/skill-pilot.git`
- The user must specify what work to contribute: commits to cherry-pick, or changes to re-apply

If `origin` is missing or still points to the official repo, stop and run the add-remote flow first.

### Create the contribution branch

1. Fetch latest remote data:

```bash
git fetch upstream
git fetch origin
```

2. Create a clean feature branch from official `contrib`:

```bash
git checkout -b <feature-branch> upstream/contrib
```

3. Bring in the intended user work.

Preferred when clean commits already exist on `user`:

```bash
git log --oneline user
git cherry-pick <commit-id>
```

Repeat cherry-pick as needed. If the change is small or not yet committed, re-apply it manually on the contribution branch instead of copying the whole `user` branch history.

4. Push the feature branch to the user's fork:

```bash
git push -u origin <feature-branch>
```

### Open the pull request

Before opening GitHub, warn the user about prompt injection risk and confirm that `github.com` is trusted.

Then use the browser agent skill to open the pull request with:

- Base repository: `X-School-Academy/skill-pilot`
- Base branch: `contrib`
- Head repository: the user's fork
- Compare branch: `<feature-branch>`

Confirm the PR is clean and does not include unrelated `user` branch history before submission.
