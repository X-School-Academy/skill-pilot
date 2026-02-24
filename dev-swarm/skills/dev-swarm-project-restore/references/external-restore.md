# External Restore (Remote Git or Local Codebase)

## Goal

Bring an existing codebase into the workspace root, restore `{SRC}/`, and preserve source provenance.

## Remote Git Repository

1. Confirm the repo URL and (optional) ref (branch/tag/SHA).
2. Decide with the user whether to:
   - Add as a submodule at `{SRC}/` (preferred when preserving history), or
   - Clone into `{SRC}/` (when submodules are not desired).
3. If using a submodule:
   ```bash
   git submodule add <repo-url> {SRC}
   git submodule update --init --recursive
   ```
4. If a ref is provided, check it out inside `{SRC}/`:
   ```bash
   git -C {SRC} checkout <ref>
   ```
5. Record the source repo and ref in your notes for the restore summary.

## Local Codebase

1. Confirm the local path and whether it is a git repo.
2. Decide with the user whether to:
   - Add as a local submodule (`git submodule add <path> {SRC}`), or
   - Copy into `{SRC}/` when no git history exists.
3. If copying:
   - Copy the code into `{SRC}/`
   - `git add {SRC}` after verifying the contents
4. Record the source path and any missing history in your notes.

## Post-Restore Check

- Ensure `{SRC}/` exists and contains the codebase
- Run `git status -s` and review with the user
- If docs are missing, proceed to `references/reverse-engineering.md`