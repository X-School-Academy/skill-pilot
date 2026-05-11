#!/usr/bin/env bash
set -e
set -o pipefail

usage() {
  echo "Usage: $0 [--ours] [--dry-run] [source-worktree-path-or-branch]"
  echo
  echo "Merge the paired worktree branch into the current branch."
  echo "Run from the main worktree to merge a linked worktree into main."
  echo "Run from a linked worktree to merge the main worktree into it."
  echo
  echo "Options:"
  echo "  --ours     Resolve conflicting hunks by favoring the current branch, default theirs."
  echo "  --dry-run  Print the planned merge command without running it."
}

current_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$current_root" ]; then
  echo "This script must be run inside a git repository."
  exit 1
fi

current_root="$(cd "$current_root" && pwd -P)"
cd "$current_root"

strategy_option="theirs"
dry_run=0
source_arg=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --ours)
      strategy_option="ours"
      ;;
    --dry-run)
      dry_run=1
      ;;
    --)
      shift
      if [ "$#" -gt 0 ]; then
        if [ -n "$source_arg" ]; then
          echo "Only one source worktree path or branch may be provided."
          exit 1
        fi
        source_arg="$1"
        shift
      fi
      if [ "$#" -gt 0 ]; then
        echo "Unexpected extra arguments: $*"
        exit 1
      fi
      break
      ;;
    -*)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
    *)
      if [ -n "$source_arg" ]; then
        echo "Only one source worktree path or branch may be provided."
        exit 1
      fi
      source_arg="$1"
      ;;
  esac
  shift
done

worktree_list="$(git worktree list --porcelain)"
worktree_count="$(printf "%s\n" "$worktree_list" | awk '$1 == "worktree" { count++ } END { print count + 0 }')"

if [ "$worktree_count" -lt 2 ]; then
  echo "No linked worktree found. Nothing to merge."
  exit 1
fi

main_path="$(printf "%s\n" "$worktree_list" | awk '$1 == "worktree" { print substr($0, 10); exit }')"
main_path="$(cd "$main_path" && pwd -P)"
current_branch="$(git branch --show-current)"

if [ -z "$current_branch" ]; then
  echo "Current worktree is not on a branch; refusing to merge into detached HEAD."
  exit 1
fi

lookup_worktree_branch_by_path() {
  wanted_path="$(cd "$1" 2>/dev/null && pwd -P || true)"
  [ -n "$wanted_path" ] || return 1

  printf "%s\n" "$worktree_list" | awk -v wanted_path="$wanted_path" '
    $1 == "worktree" {
      path = substr($0, 10)
      branch = ""
      next
    }
    $1 == "branch" {
      branch = $2
      sub("^refs/heads/", "", branch)
      if (path == wanted_path) {
        print branch
        found = 1
        exit
      }
    }
    END {
      if (!found) {
        exit 1
      }
    }
  '
}

linked_worktree_paths() {
  printf "%s\n" "$worktree_list" | awk -v main_path="$main_path" '
    $1 == "worktree" {
      path = substr($0, 10)
      if (path != main_path) {
        print path
      }
    }
  '
}

source_ref=""

if [ -n "$source_arg" ]; then
  if [ -d "$source_arg" ]; then
    source_ref="$(lookup_worktree_branch_by_path "$source_arg" || true)"
    if [ -z "$source_ref" ]; then
      echo "No worktree branch found for path: $source_arg"
      exit 1
    fi
  else
    source_ref="$source_arg"
  fi
elif [ "$current_root" = "$main_path" ]; then
  linked_count="$(linked_worktree_paths | awk 'NF { count++ } END { print count + 0 }')"
  if [ "$linked_count" -ne 1 ]; then
    echo "Found $linked_count linked worktrees. Pass the source worktree path or branch explicitly."
    linked_worktree_paths | sed 's/^/  /'
    exit 1
  fi

  source_path="$(linked_worktree_paths)"
  source_ref="$(lookup_worktree_branch_by_path "$source_path" || true)"
else
  source_ref="$(lookup_worktree_branch_by_path "$main_path" || true)"
fi

if [ -z "$source_ref" ]; then
  echo "Could not determine source branch."
  exit 1
fi

if [ "$source_ref" = "$current_branch" ]; then
  echo "Source branch is the same as current branch ($current_branch); nothing to merge."
  exit 0
fi

if ! git diff --quiet -- config || ! git diff --cached --quiet -- config; then
  echo "config has uncommitted changes. Commit, stash, or restore it before worktree merge."
  exit 1
fi

echo "Current worktree: $current_root"
echo "Current branch:   $current_branch"
echo "Source branch:    $source_ref"
echo "Strategy option:  -X $strategy_option"
echo "Dry run:          $dry_run"
echo

merge_message="Merge $source_ref into $current_branch"
merge_cmd=(git -c submodule.recurse=false merge -X "$strategy_option" --no-commit --no-ff "$source_ref")
restore_config_cmd=(git restore --source=HEAD --staged --worktree -- config)
commit_cmd=(git commit -m "$merge_message")

printf "Command: git -c submodule.recurse=false merge -X \"%s\" --no-commit --no-ff \"%s\"\n" "$strategy_option" "$source_ref"
echo "Command: git restore --source=HEAD --staged --worktree -- config"
printf "Command: git commit -m \"%s\"\n" "$merge_message"

if [ "$dry_run" = "1" ]; then
  exit 0
fi

set +e
"${merge_cmd[@]}"
merge_status="$?"
set -e

"${restore_config_cmd[@]}"

if [ "$merge_status" -ne 0 ]; then
  echo "Merge stopped with conflicts. Protected path restored: config"
  exit "$merge_status"
fi

if git diff --cached --quiet; then
  echo "Only protected paths changed; aborting merge."
  git merge --abort
  exit 0
fi

"${commit_cmd[@]}"
