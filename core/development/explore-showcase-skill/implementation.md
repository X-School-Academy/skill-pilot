# Implementation Summary

## What was built

### Data schema (`core/engine/data/AGENTS.md`)
Documented six new supported sample fields: `goals`, `zip-files-url`, `video_prompt`, `tutorial_prompt`, `terms`, and updated `links` to support an optional `prompt` key per entry.

Of these, **only `goals` and `terms` are exposed in the API response and shown in the UI**. The remaining four (`zip-files-url`, `video_prompt`, `tutorial_prompt`, `links[].prompt`) are read directly from the YAML by the `explore-showcase` skill or by future backend behavior (unzip-on-start), and are deliberately **not** exposed through the API.

### Engine normalizer (`core/engine/routes.py`)
- `_normalize_showcase_link`: returns only `{ name, url }`. The `prompt` field in the YAML is intentionally dropped from the API response.
- `_normalize_showcase_sample`: reads `goals` and `terms` and adds them to the API response. The other new fields are not normalized or returned.

### WebUI (`core/webui/components/explore/ExploreView.tsx`)
- `ShowcaseSample` interface: added `goals: string | null` and `terms: string[]`.
- Added `toKebabCase()` helper for term URL formatting.
- Added `openFileContent()` async function fetching from `/api/files/read`.
- Added `fileModal` state for the file content popup.
- **Goals section**: rendered after the Prompt section when `goals` is non-empty; markdown via `renderMarkdown`.
- **Keywords section**: rendered after Goals when `terms` is non-empty; each term is a clickable Mantine `Badge` opening `https://skill-pilot.ai/explore/terms?slug={id}&term={kebab-term}` in a new tab.
- **Files section**: extracted from the generic `pathGroups` loop; renders only the file basename with the `IconFile` icon; clicking opens a Modal popup with raw file content.
- Added file content Modal at the bottom of the component using `ScrollArea` + `<pre>`.

### New system agent skill (`core/skills/system/explore-showcase/SKILL.md`)
Full skill following the project convention (YAML frontmatter with `name`/`description`, `When to Use`, `Roles`, `Role Communication`, `Instructions`), covering: 4 audience types, 13 showcase types, content structure, and a 3-step workflow (draft yaml → generate assets → publish).

### vibe-coding skill (`references/implement.md`)
Added Step 0: copy `requirements.md` / `update.md` / `issues.md` from `workspace/showcases/{id}/` to the showcase `directory` if not already present.

### codeware skill (`references/feature-lifecycle-implement.md`)
Added Step 0: same showcase file copy logic.

## What was verified

- `pnpm tsc --noEmit` in `core/webui`: no errors.
- `python3 -c "import ast; ast.parse(...)"` on `routes.py`: parses cleanly.

## API-exposed fields (final)

Returned by `/api/explore/showcases` for each sample: all previously-existing fields plus `goals: string | null` and `terms: string[]`. Nothing else from the new schema is exposed.

## Backend / skill-only fields (not in API)

- `zip-files-url` — used by the future template-start unzip logic; reads YAML directly.
- `video_prompt` / `tutorial_prompt` — used by the `explore-showcase` skill when generating media.
- `links[].prompt` — used by the `explore-showcase` skill when generating linked resource content.

## Remaining notes

- The actual auto-unzip behavior for `zip-files-url` on template start is **not implemented** here; it requires a separate engine template API change.
- `Badge` keyboard activation for the Keywords section is not added; clicking works but a screen-reader user can't activate via Enter. Minor accessibility nit.
