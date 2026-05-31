# Plan: Explore Showcase Skill Feature

## Summary

Implement three areas of work:
1. Extend the sample YAML data schema in `AGENTS.md` and the engine normalizer
2. Update the Explore webUI with Goals section, Keywords section, and filename-only Files display
3. Create a new `explore-showcase` system agent skill

---

## Part 1 — Data Schema Updates

### `core/engine/data/AGENTS.md`

Add these fields to the **Supported sample fields** list:

| Field | Type | Description |
|---|---|---|
| `goals` | string (markdown list) | Expected outcomes after the user completes the task |
| `zip-files-url` | string or null | URL to a zip file auto-unzipped to `workspace/showcases/{id}/` on template start |
| `video_prompt` | string or null | Prompt used by the explore-showcase skill to create the showcase video (not displayed in UI) |
| `tutorial_prompt` | string or null | Prompt used by the explore-showcase skill to create the online interactive tutorial (not displayed in UI) |
| `terms` | string[] | Technology terms users can explore afterwards |

Update `links` format from `{ name, url }` to `{ name, url, prompt }` where `prompt` is optional and used only by the explore-showcase skill for generating linked resource content (not displayed in UI).

### `core/engine/routes.py`

- `_normalize_showcase_link`: pass through optional `prompt` field
- `_normalize_showcase_sample`: read and return `goals`, `zip_files_url`, `video_prompt`, `tutorial_prompt`, `terms`

---

## Part 2 — WebUI Updates (`ExploreView.tsx`)

### Interface changes
- `ShowcaseLink`: add optional `prompt?: string`
- `ShowcaseSample`: add `goals: string | null` and `terms: string[]`

### New: Goals section (after Prompt section)
- Only rendered if `sample.goals` is non-empty
- Heading: **Goals**
- Renders markdown with `renderMarkdown()`
- Same card/border styling as adjacent sections

### New: Keywords section (after Goals section)
- Only rendered if `sample.terms` is non-empty
- Heading: **Keywords**
- Each term rendered as a clickable `Badge`
- On click: opens `https://skill-pilot.ai/explore/terms?slug={sample.id}&term={kebab(term)}` in a new tab
- Terms kebab-cased: lowercase, spaces → hyphens, non-alphanumeric stripped

### Changed: Files section
- Display only the **basename** of each path (e.g., `requirements.md` instead of `workspace/showcases/foo/requirements.md`)
- Clicking a filename opens a Modal popup showing the raw file content fetched via the engine file API
- File content shown in a scrollable `<pre>` block inside the modal

---

## Part 3 — New System Agent Skill

Create `core/skills/system/explore-showcase/SKILL.md` covering:

- Audience overview (4 types)
- 13 showcase types
- Content structure per showcase
- 3-step workflow:
  1. Draft and write `workspace/showcases/{id}/showcase.yaml` → ask for review
  2. Generate assets (image/video/tutorial) → save to `assets/` → update `files.yaml` → ask for review
  3. After approval: update `core/engine/data`, copy assets to `core/webui/public/showcases/{category}/`

---

## Part 4 — Update vibe-coding and codeware skills

In the `implement` or `initial` reference of each skill, add a step:

> If the sample has a `directory` field and a `requirements.md` (or `update.md`, `issues.md`) under `workspace/showcases/{id}/`, copy those files to the target `directory` before starting.

---

## Files Changed

| File | Change |
|---|---|
| `core/engine/data/AGENTS.md` | Add new fields; update links format |
| `core/engine/routes.py` | Extend normalizer for new fields |
| `core/webui/components/explore/ExploreView.tsx` | Goals, Keywords, Files UI changes |
| `core/skills/system/explore-showcase/SKILL.md` | New file |
| `core/skills/system/vibe-coding/references/feature-lifecycle-implement.md` | Add requirements.md copy step |
| `core/skills/system/codeware/references/feature-lifecycle-implement.md` | Add requirements.md copy step |

---

## Out of Scope

- Backend: actually unzipping `zip-files-url` on template start (engine template API change needed separately)
- Image/video generation logic inside explore-showcase skill (delegates to existing skills)
