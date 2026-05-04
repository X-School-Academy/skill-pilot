#!/usr/bin/env bash
set -e

git submodule update --remote --merge

git submodule foreach '
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Submodule $name has uncommitted changes. Please commit/push inside it first."
    exit 1
  fi
'

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