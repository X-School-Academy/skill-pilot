# Contribute / Pull Request Workflow

Use this when adding features and contributing through `contrib`.

## Rule

For `contrib`, use squash merge only. Do not merge full branch history.

## Steps

1. Run update workflow first.
- Complete all steps in `update.md`.

2. Start feature work from `user`.
```bash
git checkout user
git pull --ff-only origin user
git checkout -b user/feature-<name>
```

3. Implement feature and commit in feature branch.
```bash
git add .
git commit -m "feat: <feature summary>"
```

4. Bring feature into `contrib` with squash merge.
```bash
git checkout contrib
git pull --ff-only origin contrib
git merge --squash user/feature-<name>
git commit -m "feat: <feature summary> (squash)"
```

5. Fix conflicts if any during squash.
```bash
git status
# edit conflict files
git add <resolved-files>
git commit -m "fix: resolve merge conflicts for <feature>"
```

6. Test before push.
```bash
# run project tests/lint/build here
```

7. Push `contrib`.
```bash
git push origin contrib
```

8. Create pull request from `contrib` to `codeware`.
- Title should summarize the feature.
- Include test evidence and risk notes.

## Optional Sync Back to User

After `contrib` updates:
```bash
git checkout user
git pull --ff-only origin user
git merge contrib
git push origin user
```

Resolve conflicts and retest if needed.
