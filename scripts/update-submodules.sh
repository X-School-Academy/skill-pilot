#!/usr/bin/env bash
set -e

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git submodule update --remote --merge

git submodule foreach '
  status="$(git status --porcelain=v1 --untracked-files=all)"
  if [ -n "$status" ]; then
    echo "Submodule $name has uncommitted or untracked changes:"
    printf "%s\n" "$status"
    echo "Please commit/push inside it first, or stash/remove untracked files."
    exit 1
  fi
'

if [ -f .gitmodules ]; then
  git add .gitmodules
fi

git submodule foreach --quiet 'echo "$sm_path"' | while read -r submodule_path; do
  git add "$submodule_path"
done

if git diff --cached --quiet; then
  echo "No submodule updates to commit."
  exit 0
fi

git status
git commit -m "Update submodules"
git push --recurse-submodules=on-demand
