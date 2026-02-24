# Project Restore Procedure

## Pre-Flight

1. Confirm which archive folder to restore from `99-archive/`.
2. Confirm whether to restore into the current workspace root (expected default).
3. Verify there are no conflicting files/folders in the root that would be overwritten.

## Restore Core Project Files

1. Move archived stage folders back to the root:
   - `00-*` through `10-*`
2. Move `features/` back to the root.
3. Move `ideas.md` back to the root if it exists in the archive.

Use `git mv` for tracked content. Use `mv` + `git add` for any untracked items.

## Restore {SRC} Submodule

Use the submodule restore guide in `references/submodule-restore.md`.

## Post-Restore Checks

1. Verify all stage folders exist at the root.
2. Verify `ideas.md` exists at the root if it was part of the archived snapshot.
3. Verify `{SRC}/` is a submodule and points to the expected commit.
4. Run `git status -s` and review with the user.

## User Approval

Summarize:
- What was restored
- The archive source folder
- The `{SRC}` submodule commit

Ask if the user wants to commit the changes.