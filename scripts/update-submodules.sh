#!/usr/bin/env bash
set -e
set -o pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

rewrite_local_submodule_history="${REWRITE_LOCAL_SUBMODULE_HISTORY:-0}"
history_rewritten=0

check_clean_submodules() {
  git submodule foreach '
    status="$(git status --porcelain=v1 --untracked-files=all)"
    if [ -n "$status" ]; then
      echo "Submodule $name has uncommitted or untracked changes:"
      printf "%s\n" "$status"
      echo "Please commit/push inside it first, or stash/remove untracked files."
      exit 1
    fi
  '
}

check_staged_submodule_commits_are_remote_visible() {
  git submodule foreach --quiet 'echo "$sm_path"' | while IFS= read -r submodule_path; do
    [ -n "$submodule_path" ] || continue

    staged_sha="$(git ls-files -s -- "$submodule_path" | awk '$1 == "160000" { print $2 }')"
    [ -n "$staged_sha" ] || continue

    submodule_url="$(git config --file .gitmodules --get "submodule.$submodule_path.url" || true)"
    if [ -z "$submodule_url" ]; then
      submodule_name="$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$' | awk -v path="$submodule_path" '$2 == path { sub(/^submodule\./, "", $1); sub(/\.path$/, "", $1); print $1; exit }' || true)"
      submodule_url="$(git config --file .gitmodules --get "submodule.$submodule_name.url" || true)"
    fi

    if [ -z "$submodule_url" ]; then
      echo "Could not find remote URL for submodule $submodule_path in .gitmodules."
      exit 1
    fi

    if ! git -C "$submodule_path" fetch --quiet origin; then
      echo "Could not fetch remote refs for submodule $submodule_path."
      exit 1
    fi

    if ! git -C "$submodule_path" branch -r --contains "$staged_sha" | grep -q .; then
      echo "Refusing to commit submodule $submodule_path at local-only commit $staged_sha."
      echo "That commit is not reachable from any remote branch in $submodule_url."
      echo "Switch the submodule to a remote-visible commit before updating the parent repo,"
      echo "or push the submodule commit first if it is meant to be shared."
      exit 1
    fi
  done
}

upstream_ref() {
  git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true
}

find_unpushed_local_only_submodule_gitlinks() {
  upstream="$(upstream_ref)"
  if [ -z "$upstream" ]; then
    return 0
  fi

  git submodule foreach --quiet 'git fetch --quiet origin'

  git rev-list --reverse "$upstream..HEAD" | while IFS= read -r commit_sha; do
    [ -n "$commit_sha" ] || continue

    git submodule foreach --quiet 'echo "$sm_path"' | while IFS= read -r submodule_path; do
      [ -n "$submodule_path" ] || continue

      gitlink_sha="$(git ls-tree "$commit_sha" -- "$submodule_path" | awk '$1 == "160000" { print $3 }')"
      [ -n "$gitlink_sha" ] || continue

      if ! git -C "$submodule_path" branch -r --contains "$gitlink_sha" | grep -q .; then
        commit_subject="$(git log -1 --format=%s "$commit_sha")"
        printf "%s\t%s\t%s\t%s\n" "$commit_sha" "$submodule_path" "$gitlink_sha" "$commit_subject"
      fi
    done
  done
}

rewrite_unpushed_history_with_current_tree() {
  upstream="$(upstream_ref)"
  if [ -z "$upstream" ]; then
    echo "No upstream branch is configured; cannot rewrite unpushed history safely."
    exit 1
  fi

  if [ "$(git rev-list --count "$upstream..HEAD")" = "0" ]; then
    return 0
  fi

  echo "Rewriting unpushed parent commits so they no longer reference local-only submodule commits."
  echo "Old HEAD: $(git rev-parse HEAD)"
  echo "Upstream: $upstream ($(git rev-parse "$upstream"))"

  git reset --soft "$upstream"

  if git diff --cached --quiet; then
    echo "Nothing staged after history rewrite."
    exit 0
  fi

  check_staged_submodule_commits_are_remote_visible

  git status
  git commit -m "Update local changes"
  history_rewritten=1
}

handle_unpushed_local_only_submodule_gitlinks() {
  bad_gitlinks="$(find_unpushed_local_only_submodule_gitlinks)"
  if [ -z "$bad_gitlinks" ]; then
    return 0
  fi

  echo "Unpushed parent commits reference local-only submodule commits:"
  printf "%s\n" "$bad_gitlinks" | while IFS="$(printf '\t')" read -r commit_sha submodule_path gitlink_sha commit_subject; do
    echo "  $commit_sha ($commit_subject)"
    echo "    $submodule_path -> $gitlink_sha"
  done

  if [ "$rewrite_local_submodule_history" != "1" ]; then
    echo
    echo "The needed fix is to rewrite the unpushed parent commits so none of them reference local-only submodule commits."
    echo "To do that with this script, run:"
    echo "  REWRITE_LOCAL_SUBMODULE_HISTORY=1 ./scripts/update-submodules.sh"
    exit 1
  fi

  rewrite_unpushed_history_with_current_tree
}

check_clean_submodules

git submodule update --remote --checkout

check_clean_submodules

git submodule foreach '
  current_sha="$(git rev-parse HEAD)"
  if ! git fetch --quiet origin; then
    echo "Could not fetch remote refs for submodule $name."
    exit 1
  fi
  if ! git branch -r --contains "$current_sha" | grep -q .; then
    echo "Submodule $name is checked out at local-only commit $current_sha."
    echo "Refusing to record it in the parent repository."
    exit 1
  fi
'

if [ -f .gitmodules ]; then
  git add .gitmodules
fi

git submodule foreach --quiet 'echo "$sm_path"' | while read -r submodule_path; do
  git add "$submodule_path"
done

check_staged_submodule_commits_are_remote_visible
handle_unpushed_local_only_submodule_gitlinks

if git diff --cached --quiet && [ "$history_rewritten" != "1" ]; then
  echo "No submodule updates to commit."
  exit 0
fi

if [ "$history_rewritten" != "1" ]; then
  git status
  git commit -m "Update submodules"
  handle_unpushed_local_only_submodule_gitlinks
fi

git push --recurse-submodules=on-demand
