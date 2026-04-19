# AGENTS — about/

Rules for AI agents when upgrading or restoring Skill Pilot. Read this file before changing any code after a sync, reset, or checkout that advances the repo.

## Source of truth

- Applied Skill Pilot version: `about/version.json5` → `{ version, build }`.
- Applied workspace version: `workspace/config/version.json5` → `{ version }`.
- Available Skill Pilot versions: files under `about/changelog/` (one file per version; each file contains one or more `## Build <n>` sections).
- Index for human reading: `about/CHANGELOG.md`. Do not rely on the index for decisions — use the files themselves.

## When to run

Run the upgrade procedure whenever the repo state advances past `about/version.json5`. That includes:

- After `git merge upstream/codeware` or equivalent sync.
- After `git reset --hard upstream/codeware` (restore).
- After any checkout that moves `about/changelog/` forward.

If the checked-out files show a version tag newer than `about/version.json5`, there are pending builds to apply.

## Upgrade procedure

1. Read the applied state:
   - `applied_version`, `applied_build` from `about/version.json5`.
   - `applied_workspace` from `workspace/config/version.json5`.
2. Enumerate pending builds:
   - List every `about/changelog/<version>.md` file.
   - Inside each file, list every `## Build <n>` section.
   - A build is **pending** if `(version, build)` is strictly greater than `(applied_version, applied_build)`.
   - Compare versions lexicographically segment-by-segment after splitting on `_`. Compare builds numerically.
3. Sort pending builds in ascending order. Apply them one at a time, oldest first.
4. For each pending build:
   a. Apply every step in its `### Upgrade notices` in the stated order. Notices are authoritative — do not skip, reorder, or merge them.
   b. If the build specifies a `### Workspace target` that differs from the current `workspace/config/version.json5`:
      - Perform the workspace migration steps from that build's notices.
      - Write the new version into `workspace/config/version.json5`.
   c. After the build's steps succeed, update `about/version.json5` to this build's `(version, build)`.
   d. If a step fails, stop. Do not advance `about/version.json5` past the failing build. Report the failing build and step clearly.
5. After the last pending build, confirm:
   - `about/version.json5` matches the newest `(version, build)` on disk.
   - `workspace/config/version.json5` matches the `Workspace target` of that newest build.

## Restore procedure

A restore hard-resets the repo to `upstream/codeware`. After the reset:

1. Do **not** assume `about/version.json5` was brought along by the reset — it was, but the on-disk version file now reflects the latest release, not the user's previously-applied state. Before the reset, the caller must have recorded the pre-reset `(applied_version, applied_build, applied_workspace)`.
2. Set `about/version.json5` back to the recorded pre-reset `(applied_version, applied_build)` so the upgrade procedure can walk forward cleanly. Leave `workspace/config/version.json5` at the recorded pre-reset workspace version.
3. Run the standard **Upgrade procedure** above.

This guarantees that a restore does not silently skip workspace migrations that the user had not yet applied.

## Constraints

- Never edit `about/changelog/*.md` files during an upgrade. They are the migration instructions; they are not the migration record.
- Never write a future `(version, build)` into `about/version.json5` before its notices have been fully applied.
- Never downgrade `about/version.json5` or `workspace/config/version.json5` except as part of the restore procedure's explicit rollback step.
- If a notice cannot be applied automatically (needs user input, destructive action, or network access), stop and ask the user before continuing.

## Adding a new release (maintainers)

When cutting a new Skill Pilot version or build:

1. Add or edit `about/changelog/<version>.md`. Add a new `## Build <n>` section at the top of the file for the version you are releasing.
2. Fill in `### Changes since previous`, `### Upgrade notices`, and `### Workspace target`.
3. If this is a new version (new file), add an entry to the top of `about/CHANGELOG.md`.
4. Do **not** edit `about/version.json5` in the release commit. That file tracks the *applied* state on a given checkout; the upgrade procedure bumps it when users pull the release.
