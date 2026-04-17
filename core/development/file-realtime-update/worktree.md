# File Manager Worktree Support Summary

## Request Summary

Add worktree-aware behavior to the File Manager with these rules:

1. Hide the `.git` folder from the File Manager tree and folder contents.
2. Replace the generic `Project` root label with the actual project folder name, for example `skill-pilot-haicam`.
3. If `.git/worktrees/*/gitdir` exists, resolve the referenced worktree folders and show them in File Manager so the tree can browse both the main repo and its worktrees.
4. If worktrees exist, the project folder and each worktree folder must support folding in the directory tree.
5. File realtime updates must also monitor worktree folders so File Manager refreshes automatically.

## Scope Clarification

User clarification narrowed the feature:

1. Worktree support applies only inside File Manager.
2. Other WebUI areas such as Tasks, Dev Swarm, and other main-menu pages must remain bound to the main repo only.
3. If the current project folder itself is a worktree checkout, do not show the main repo folder or sibling worktree folders.
4. Multi-root worktree behavior should only be enabled when the current project is the main repo and it has attached worktrees.

## Implementation Summary

### Backend

Updated `core/engine/routes.py` to make File Manager worktree-aware without changing the rest of the WebUI:

1. `.git` is now excluded from File Manager listings.
2. File Manager root metadata now returns:
   - `projectName`
   - `supportsWorktrees`
   - `roots`
3. Added main-repo-only worktree discovery from `.git/worktrees/*/gitdir`.
4. Added a File Manager virtual-root model:
   - single-root mode keeps existing `/` behavior
   - multi-root mode exposes virtual roots for:
     - the main project
     - each discovered worktree
5. Updated file path normalization, read/write, rename, copy, move, mkdir, upload, and download handling so File Manager paths can resolve to either the main repo or a discovered worktree.
6. Protected-path checks such as `config/.env` now remain relative to each selected root.
7. Virtual File Manager roots are read-only containers:
   - cannot rename them
   - cannot delete them
   - cannot copy or move them
   - cannot create folders in the virtual top-level workspace node

### Realtime Watcher

Updated `core/engine/file_realtime.py`:

1. The shared watcher now supports multiple watched roots instead of a single repo root.
2. The watcher dynamically resolves active roots from File Manager root discovery.
3. Realtime changes from both the main repo and discovered worktrees now flow through the same SSE channel used by File Manager.
4. `.git` is excluded from watcher noise just like it is excluded from listings.

### Frontend

Updated `core/webui/components/FileManagerContent.tsx`:

1. The File Manager root label now uses the actual project folder name.
2. Added File Manager metadata loading from `/api/files/info`.
3. Added support for File Manager root entries with:
   - label
   - root kind
   - virtual root flag
4. In multi-root mode, the left tree renders the project root and each worktree root as foldable top-level folders.
5. Display paths shown in the header and content panel now use friendly labels based on the project/worktree folder names.
6. Context menu and add actions are restricted when the user is on the virtual top-level workspace node or on virtual root containers.
7. Relative path copy now strips the selected root prefix so copied paths stay meaningful inside each project/worktree root.

## Result

Current behavior after implementation:

1. `.git` is hidden from File Manager.
2. The main project label shows the actual folder name.
3. When the current project is the main repo and has worktrees, File Manager shows:
   - the main project folder
   - each discovered worktree folder
4. These project/worktree roots are foldable in the left tree.
5. Realtime updates now cover discovered worktree folders for File Manager refresh behavior.
6. Other WebUI main-menu pages remain unchanged and still bind to the main repo.
7. If the current project is itself a worktree checkout, File Manager stays in single-root mode and does not show the main repo or sibling worktrees.

## Verification

Completed checks:

1. `python3 -m py_compile core/engine/routes.py core/engine/file_realtime.py`
2. `pnpm -C core/webui exec tsc --noEmit`
3. Targeted runtime sanity check with `uv --directory core/engine run python` confirming:
   - discovered File Manager roots
   - path normalization for main project root
   - path normalization for worktree root

## Files Changed

Implementation was applied in:

1. `core/engine/routes.py`
2. `core/engine/file_realtime.py`
3. `core/webui/components/FileManagerContent.tsx`
