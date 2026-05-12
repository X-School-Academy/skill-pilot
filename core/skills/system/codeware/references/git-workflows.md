# Git Workflows

Use these procedures for codeware `update` and `restore`.

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

Goal: keep `user` current by merging the latest official `codeware`, then apply any pending upgrade notices so `about/version.json5` and `workspace/config/version.json5` reflect the new state.

1. Require a clean working tree. If there are local changes, ask the user whether to commit or stash them first.
2. Record the pre-merge applied state:

```bash
cat about/version.json5
cat workspace/config/version.json5
```

Remember `(applied_version, applied_build)` and `applied_workspace`. These are needed by Step 7.

3. Fetch the official repo:

```bash
git fetch upstream
```

4. Switch to `user`:

```bash
git checkout user
```

5. Merge official changes:

```bash
git merge upstream/codeware
```

6. If conflicts occur:
- Resolve them file by file
- Prefer preserving user-specific work while integrating official fixes
- Re-run targeted tests or startup checks
- For `about/version.json5`: keep the pre-merge `(applied_version, applied_build)`. Step 7 will bump it after notices are applied. Do not take the incoming "ours vs. theirs" newer value blindly.
- For `workspace/config/version.json5`: keep the pre-merge workspace version. Step 7 will bump it according to each build's `Workspace target`.

7. Apply pending upgrade notices from `about/changelog/`:

- List every `## Build <n>` section across `about/changelog/*.md`.
- Select sections whose `(version, build)` is strictly greater than the pre-merge `(applied_version, applied_build)`.
- In ascending order:
  - Apply the build's `### Upgrade notices` in order.
  - If the build's `### Workspace target` differs from the current `workspace/config/version.json5`, apply the workspace migration steps from the notices, then update `workspace/config/version.json5` to that target.
  - Write the build's `(version, build)` into `about/version.json5`.
  - On failure: stop, leave `about/version.json5` at the last successfully applied build, and report.

8. Report what changed, which builds were applied, and whether the `user` branch is now ahead of its fork remote.

## Restore flow

Use this only when the `user` branch is broken and a normal fix or merge is not viable.

This is destructive. Require explicit user approval before the reset step.

1. Record the pre-reset applied state before touching anything:

```bash
cat about/version.json5
cat workspace/config/version.json5
```

Remember `(applied_version, applied_build)` and `applied_workspace`. The reset will overwrite `about/version.json5` on disk with the version from `upstream/codeware`, but the agent must treat the pre-reset values as the true applied state.

2. Fetch the official repo:

```bash
git fetch upstream
```

3. Create a backup branch from the current `user` state:

```bash
git checkout user
git branch "backup/user-$(date +%Y%m%d-%H%M%S)"
```

4. Hard-reset `user` to the official `codeware` branch:

```bash
git reset --hard upstream/codeware
```

5. Restore the pre-reset applied state into the version files so the upgrade walk starts from the correct position:

- Rewrite `about/version.json5` to the pre-reset `(applied_version, applied_build)`.
- Rewrite `workspace/config/version.json5` to the pre-reset workspace version.

These writes are local only; they are not committed. Do not skip this step; without it, any workspace migrations between the user's previous applied state and the newest release would be silently skipped.

6. Apply pending upgrade notices exactly as in Step 7 of the update flow. This brings both version files forward to the newest release's state, running every migration in between.

7. Verify the restored baseline and fix any remaining local environment or project errors.

8. If the user wants selected work recovered from the backup branch, do it intentionally with targeted cherry-picks or file restores instead of replaying the whole broken state.

## Conflict handling rules

- Do not discard unrelated user edits during a normal `update`
- During `restore`, preserve recoverability by creating the backup branch first
- If conflicts touch generated files and source files, resolve source first and regenerate artifacts second
- If the conflict meaning is unclear, stop and ask rather than guessing

## Version files and the changelog

- `about/version.json5` tracks the applied state of this checkout. It is authoritative for "what version am I on right now."
- `about/changelog/*.md` contains the migration instructions between versions and builds. Never modify these files during an update or restore; they describe the work to do, not the work completed.
- `workspace/config/version.json5` tracks the workspace structure and config format. Bump it only when a changelog build explicitly states a new `Workspace target` and you have applied that build's workspace migration steps.
- See `about/AGENTS.md` for the full upgrade and restore procedures, including how to compare `(version, build)` pairs and what to do on failure.
