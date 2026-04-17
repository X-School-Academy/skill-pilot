# Dev Plan: Explore Start Screen and Showcase Template Launcher

## Summary

Implement an `Explore` experience backed by `core/engine/data/showcases.json5`, make it the default root experience inside the existing `/` page, and add a sample-detail workflow with production-only template launching. The current root `/?new_session=true...` flow stays intact; it continues to force the existing new-session composer, while normal `/` loads Explore by default.

## Key Changes

### 1. Backend explore domain

- Add an explore API in `core/engine/routes.py` with:
  - `GET /api/explore/showcases`
  - `POST /api/explore/template/start`
  - `GET /api/explore/template/status?launch_id=...`
- `GET /api/explore/showcases` reads `core/engine/data/showcases.json5`, validates the current schema, and returns normalized category/sample data without changing the file format.
- Normalize local asset paths for `thumbnail`, `video`, and local `tutorial` files into URLs using the existing `/api/files/download` route; keep external `http/https` URLs unchanged.
- Treat `skills`, `tools`, and `files` as repo-relative path strings. The UI will open them through File Manager when clicked.
- Add launch-state helpers for:
  - resolving a sample by `id`
  - computing worktree path as sibling dir: `<repo parent>/<repo name>_<sample_id>`
  - detecting existing worktree folder
  - tracking the currently managed dev worktree instance
  - polling dev readiness on the existing dev ports
- `POST /api/explore/template/start` request shape:
  - `sample_id`
  - `use_worktree`
  - `checkout_tag`
  - `start_in_dev_mode`
  - optional `existing_worktree_action: continue | remove`
  - optional `running_dev_action: reuse | restart`
- `POST /api/explore/template/start` response states:
  - `launched` with target URL
  - `pending` with `launch_id`
  - `needs_existing_worktree_action`
  - `needs_running_dev_action`
  - `error`
- Worktree launch behavior:
  - if `use_worktree` is `false`, do not create or modify worktrees; return the production new-session URL with the sample prompt
  - if `use_worktree` is `true`, optionally checkout `git_tag`, then start the full worktree dev stack from the worktree root with `./skillpilot.sh --dev`
  - if another dev instance is already tracked for a different worktree, require explicit `restart`
  - if the tracked dev instance already matches the requested worktree, reuse it
- Stop/restart behavior uses `./skillpilot.sh stop --dev` and `./skillpilot.sh --dev` in the tracked worktree root. Do not support multiple concurrent dev worktree instances.

### 2. WebUI Explore experience

- Add reusable Explore UI under `core/webui/components/explore/` and wire it into `core/webui/pages/index.tsx`.
- Extend the root page state with `ActiveView = 'explore'` and make it the default when no forcing query is present.
- Preserve current root query behavior:
  - `?new_session=true...` still opens the current composer view
  - `?new_terminal=true...` still launches shell flow
  - `?view=explore` explicitly selects Explore
- Use query state for deep-linking:
  - `view=explore`
  - `explore_mode=category|popularity|level`
  - `category=<category name>`
  - `sample=<sample id>`
- Add `Explore` as the first left-nav item, followed by a separator, in every shared/global nav surface:
  - `core/webui/pages/index.tsx`
  - `core/webui/components/main-layout.tsx`
  - `core/webui/pages/terminals/index.tsx`
- Explore browsing behavior:
  - default mode is `category`
  - `category` mode shows category tiles with generated fallback thumbnails and hover descriptions
  - clicking a category shows that category’s samples
  - `popularity` mode shows all samples sorted descending by `popularity`
  - `level` mode shows all samples sorted ascending by `level`
- Fallback thumbnails:
  - generate initials from title/category words
  - use deterministic color derived from category/sample id so color is stable across renders
- Sample detail behavior:
  - three-column layout inside the existing page shell
  - middle column shows media, title, description, and markdown-rendered prompt
  - right column shows `Use Template`, git tag, worktree actions, path lists, and external links
- Prompt rendering:
  - add a copy button
  - rewrite `@path` tokens into links that open `/file-manager?path=...`
  - use repo-relative paths with a leading `/` for File Manager targets
- Media behavior:
  - clicking thumbnail or `video` opens an in-page modal player for local/direct media
  - `tutorial` opens the same modal for direct media files, otherwise opens a new tab for webpage URLs

### 3. Template-launch UX

- `Use Template` is enabled only when the current runtime is production; in dev runtime show a disabled button with explanatory text.
- On click, open a settings modal with:
  - `using worktree`
  - `checkout tag` only when `git_tag` is not null
  - `start in dev mode`
- Chosen default behavior:
  - `using worktree` defaults from sample `use_worktree`
  - `checkout tag` defaults to checked when `git_tag` exists
  - when `using worktree` is true, `start in dev mode` is forced on and not allowed to become false
- Launch flow:
  - no worktree: redirect current production app to `/?new_session=true&prompt=...`
  - worktree: call `POST /api/explore/template/start`, resolve conflicts if returned, then poll `GET /api/explore/template/status`
  - while pending, show a loading state until the dev stack is reachable
  - when ready, open the dev WebUI URL with the prompt as `?new_session=true&prompt=...`
- `Open in Worktree` button is shown only when the sample’s `use_worktree` is true and uses the same backend launch flow, skipping the prompt modal defaults only if the sample already fully determines them.

## Public Interfaces

- Keep `showcases.json5` as an array of category objects with the existing fields already documented in the file comments.
- Frontend types to add:
  - `ShowcaseCategory`
  - `ShowcaseSample`
  - `ExploreMode`
  - `TemplateLaunchRequest`
  - `TemplateLaunchResponse`
  - `TemplateLaunchStatus`
- No schema expansion is required for v1 beyond the current JSON5 structure.

## Test Plan

- Backend tests:
  - valid `showcases.json5` parse and normalization
  - missing/invalid sample fields return structured errors
  - local asset path normalization uses `/api/files/download`
  - sample lookup by `id`
  - worktree path generation
  - existing worktree conflict response
  - running dev conflict response
  - launch status transitions `pending -> ready` and error path
- Frontend tests:
  - `/` defaults to Explore
  - `?new_session=true...` still opens the current new-session composer
  - nav shows `Explore` first with separator after it
  - category/popularity/level sorting and drill-in behavior
  - sample detail deep-link via query state
  - prompt copy works
  - `@path` tokens open File Manager links correctly
  - production-only `Use Template` gating
  - conflict dialogs for existing worktree and running dev instance
- Manual smoke checks:
  - local image/video/tutorial assets render correctly
  - external tutorial links open in a new tab
  - `./skillpilot.sh --dev` launch from a worktree brings up the dev WebUI and routes to a new session with the sample prompt

## Assumptions And Defaults

- Explore replaces the normal root landing state, but not the root route itself; `/` stays the main page so existing new-session query flows remain valid.
- Only one managed dev worktree instance is supported at a time because the repo’s dev ports are fixed.
- Worktree dev launches start the full Skill Pilot dev stack from the selected worktree root, not only the Next.js frontend.
- `skills`, `tools`, and `files` are stored as repo-relative paths in the JSON5 data file.
- Generated thumbnail colors are deterministic, not truly random, to avoid hydration drift and visual churn.
