# Partial and Squash Merges

Use this reference when the user asks to merge specific folders or files from one branch to another, perform a partial merge, squash merge a branch, or create a clean single-commit integration.

## Clarify Merge Requirements

Confirm the required merge type when it is not already clear:

- Partial merge: source branch, target branch, and exact files or folders.
- Squash merge: source branch, target branch, and commit message expectations.

Before changing branches or applying merge changes, check `git status --short` and avoid overwriting unrelated user work.

## Partial Merge

Use a partial merge when only selected files or folders should be taken from a source branch.

1. Switch to the target branch.
2. Check out the requested paths from the source branch.
3. Review the diff.
4. Stage only the requested paths.
5. Commit after user approval unless already authorized.

Example:

```bash
git checkout target-branch
git checkout source-branch -- path/to/folder path/to/file
git diff -- path/to/folder path/to/file
git add path/to/folder path/to/file
git commit -m "chore(scope): sync selected paths from source-branch"
```

If a requested path does not exist in the source branch, verify with:

```bash
git ls-tree -r source-branch --name-only
```

## Squash Merge

Use a squash merge when all changes from a source branch should be integrated as one clean commit.

1. Switch to the target branch.
2. Run the squash merge.
3. Resolve conflicts if needed.
4. Review staged changes.
5. Commit with a focused Conventional Commits message after user approval unless already authorized.

Example:

```bash
git checkout target-branch
git merge --squash source-branch
git status --short
git diff --staged
git commit -m "feat(scope): add summarized feature"
```

## Verification

After a partial or squash merge:

- Run `git status --short`.
- Review the final commit with `git log -1 --stat` if a commit was created.
- Run relevant tests when the merge affects executable code.
- Ask before pushing unless the user explicitly requested a push.

## Common Issues

- Uncommitted changes block checkout: ask whether to commit, stash, or stop.
- Merge conflicts during squash merge: resolve conflicts, stage resolved files, and continue with the commit.
- Wrong paths were staged: unstage or restore only those paths before committing.
