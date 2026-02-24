# Confirmation and Commit

Before committing, show the user:

1. What has been archived (list the folders/files moved)
2. The archive location (e.g., `99-archive/my-project/`)
3. The new empty structure that has been created
4. If `{SRC}/` was a submodule, note that it has been removed from submodule configuration

Ask the user:
- "The project has been archived. Do you want to commit these changes to git?"

If the user confirms:

```bash
git add .
git commit -m "Archive project and reset structure"
```

Confirm completion and remind the user they can start a new project with `ideas.md` or by running the init-ideas skill.