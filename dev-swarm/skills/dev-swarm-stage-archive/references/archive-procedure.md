# Archive Procedure

## Create Archive Folder

1. Create the archive folder path:
   - Base path: `99-archive/{project-name}`
   - If the folder already exists, append `-YYYYMMDD` suffix (e.g., `99-archive/my-project-20250115`)
   - Use the current date for the suffix
2. Create the archive folder:
   ```bash
   mkdir -p 99-archive/{archive-folder-name}
   ```

## Handle {SRC}/ Submodule (if applicable)

Check if `{SRC}/` is a git submodule using `git submodule status`.

- If `{SRC}/` is a submodule, follow `references/submodule-detach.md`.
- If `{SRC}/` is not a submodule, continue.

## Move Project Artifacts to Archive

Use `git mv` to move the following items into the archive folder:

1. All stage folders: `00-*` through `10-*`
2. `features/`
3. `{SRC}/`
4. `ideas.md` (if it exists and the user wants to archive it)

Important:
- Leave `99-archive/` in place
- Do not touch unrelated files (e.g., `.*`, `dev-swarm/`, `README.md`)
- Use `git mv` for tracked folders
- If `{SRC}/` was a submodule and is now untracked, use `mv` and then `git add`

## Recreate Empty Project Structure

Create fresh empty folders and add `.gitkeep` files:

```bash
for dir in 00-init-ideas 01-market-research 02-personas 03-mvp 04-prd 05-ux 06-architecture 07-tech-specs 08-devops 10-sprints 11-deployment features {SRC}; do
  mkdir -p "$dir"
  touch "$dir/.gitkeep"
done
```

## Handle ideas.md

- If the user wants to start a new project from `ideas.md`, keep it at the repo root.
- If the user only wants to archive, move `ideas.md` into the archive.

## Record Submodule Metadata (Recommended)

If `{SRC}/` was a submodule, record its URL and commit SHA in:

`99-archive/{archive-folder-name}/{SRC}-submodule.txt`

This helps restore the submodule later even if git history is rewritten.
