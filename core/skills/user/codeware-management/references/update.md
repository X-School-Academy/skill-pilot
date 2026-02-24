# Update Workflow (Codeware -> Contrib/User via PR)

Use this when you need to sync latest `codeware` into `contrib` and `user`.
Default policy: create pull requests from `codeware` first, then merge with conflict fixes.

## Steps

1. Update local `codeware`.
```bash
git checkout codeware
git pull --ff-only origin codeware
```

2. Create update branch for `contrib` sync.
```bash
git checkout -b sync/codeware-to-contrib contrib
git merge codeware
```

3. Resolve conflicts if any, then push and open PR to `contrib`.
```bash
git status
# edit conflict files
git add <resolved-files>
git commit
git push origin sync/codeware-to-contrib
```

Open PR: `sync/codeware-to-contrib` -> `contrib`, then merge PR.

4. Create update branch for `user` sync.
```bash
git checkout -b sync/codeware-to-user user
git merge codeware
```

5. Resolve conflicts if any, then push and open PR to `user`.
```bash
git status
# edit conflict files
git add <resolved-files>
git commit
git push origin sync/codeware-to-user
```

Open PR: `sync/codeware-to-user` -> `user`, then merge PR.

6. Validate final state.
```bash
git checkout contrib && git pull --ff-only origin contrib
git checkout user && git pull --ff-only origin user
```
