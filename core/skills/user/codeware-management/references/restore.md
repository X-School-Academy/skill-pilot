# Restore Workflow (User Branch Back to Codeware Baseline)

Use this when `user` is broken and needs rollback toward stable `codeware` behavior.

## Steps

1. Refresh both branches.
```bash
git fetch --all --prune
git checkout codeware
git pull --ff-only origin codeware
git checkout user
git pull --ff-only origin user
```

2. Compare `user` vs `codeware`.
```bash
git diff --name-status codeware...user
```

3. Roll back specific broken files in `user` to `codeware` state.
```bash
git checkout codeware -- <path1> <path2>
git add <path1> <path2>
git commit -m "fix: restore files from codeware baseline"
```

4. If broad rollback is required, open a restore branch first.
```bash
git checkout -b user/restore-<date>
git restore --source=codeware -- .
git add .
git commit -m "fix: restore user working copy to codeware baseline"
```

5. Validate working copy.
```bash
# run tests/build/smoke checks
```

6. Push restored result.
```bash
git push origin user
```

## Conflict Note

If restoring while parallel changes exist:
- Keep critical hotfix files from `user`.
- Restore everything else from `codeware`.
- Re-test and document retained deltas.
