# Git Workflows

Use these procedures for `update` and `restore`.

Official upstream repository:

- `https://github.com/X-School-Academy/skill-pilot.git`

Recommended remote layout:

- `upstream` -> official repo
- `origin` -> user's fork

## Baseline inspection

Run before changing Git state:

```bash
git branch --show-current
git status --short
git remote -v
git branch -vv
```

If `upstream` is missing, add it first:

```bash
git remote add upstream https://github.com/X-School-Academy/skill-pilot.git
```

If `origin` still points at the official repo and the user later wants a personal fork remote, use the add-remote flow in `github-contribution.md`.

## Update flow

Goal: keep `user` current by merging the latest official `codeware`.

1. Require a clean working tree. If there are local changes, ask the user whether to commit or stash them first.
2. Fetch the official repo:

```bash
git fetch upstream
```

3. Switch to `user`:

```bash
git checkout user
```

4. Merge official changes:

```bash
git merge upstream/codeware
```

5. If conflicts occur:
- Resolve them file by file
- Prefer preserving user-specific work while integrating official fixes
- Re-run targeted tests or startup checks

6. Report what changed and whether the `user` branch is now ahead of its fork remote.

## Restore flow

Use this only when the `user` branch is broken and a normal fix or merge is not viable.

This is destructive. Require explicit user approval before the reset step.

1. Fetch the official repo:

```bash
git fetch upstream
```

2. Create a backup branch from the current `user` state:

```bash
git checkout user
git branch "backup/user-$(date +%Y%m%d-%H%M%S)"
```

3. Hard-reset `user` to the official `codeware` branch:

```bash
git reset --hard upstream/codeware
```

4. Verify the restored baseline and fix any remaining local environment or project errors.

5. If the user wants selected work recovered from the backup branch, do it intentionally with targeted cherry-picks or file restores instead of replaying the whole broken state.

## Conflict handling rules

- Do not discard unrelated user edits during a normal `update`
- During `restore`, preserve recoverability by creating the backup branch first
- If conflicts touch generated files and source files, resolve source first and regenerate artifacts second
- If the conflict meaning is unclear, stop and ask rather than guessing
