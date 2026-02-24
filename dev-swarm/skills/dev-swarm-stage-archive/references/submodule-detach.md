# Submodule Detach Procedure

If `{SRC}/` is a submodule, detach it while keeping the working tree so it can be archived.

```bash
# Remove the submodule entry from .git/config
git submodule deinit -f {SRC}

# Remove the gitlink from the index but keep the working tree
git rm -f --cached {SRC}

# Remove the {SRC} entry from .gitmodules
git config -f .gitmodules --remove-section submodule.{SRC} || true
git add .gitmodules

# Detach the submodule working tree so it becomes a normal folder
rm -f {SRC}/.git

# Remove the submodule's git metadata after detaching
rm -rf .git/modules/{SRC}
```

Verify `git status -s` shows `{SRC}/` as untracked before moving it.