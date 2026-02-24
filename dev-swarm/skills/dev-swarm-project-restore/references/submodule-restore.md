# {SRC} Submodule Restore Guide

## Goal

Re-add `{SRC}/` as a git submodule and set it to the same commit it had before the archive.

## Steps

1. Check for archived submodule metadata:
   - Look for `99-archive/{archive-folder}/{SRC}-submodule.txt` and use its URL and SHA if present.
2. If metadata is not present, inspect git history to find the last commit where `.gitmodules` and the `{SRC}` gitlink existed.
   - Example: `git log -- .gitmodules` and `git log -- {SRC}`
3. From the archive metadata or git history, extract:
   - Submodule URL
   - Submodule path (expected `{SRC}`)
   - Submodule commit SHA
4. Re-add the submodule:
   ```bash
   git submodule add <url> {SRC}
   git submodule update --init --recursive
   ```
5. Check out the historical submodule commit:
   ```bash
   git -C {SRC} checkout <sha>
   ```
6. Record the restored submodule state:
   ```bash
   git add .gitmodules {SRC}
   ```

## If History Is Missing

- Ask the user for the submodule URL and expected commit SHA.
- If the commit SHA is unknown, default to the submodule's default branch and confirm with the user.

## Validation

- `git submodule status` shows `{SRC}` with the expected SHA
- `git status -s` shows staged `.gitmodules` and `{SRC}`