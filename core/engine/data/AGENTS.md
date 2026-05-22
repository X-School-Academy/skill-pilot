# Showcase Data Maintenance Rules

This folder contains the Explore showcase index and the sample YAML files it references.

## Files

- `showcases.json5`: clean category index only. Do not keep schema/docstring comments here.
- `showcases/**/*.yaml`: one sample per file. Keep fields explicit and easy to scan.

## Category Index Rules

- The top-level value in `showcases.json5` must be an array of category objects.
- Category fields:
  - `id`: stable folder id
  - `category`: display label
  - `description`: short user-facing summary
  - `thumbnail`: optional image. Accepts `http(s)://...` (remote), `/...` (webui public asset, e.g. `/showcases/foo.png`), a repo-relative path (served via the engine file API), or `null`
  - `subcategories`: optional nested category array
- Samples are discovered from matching folders under `showcases/`.
- Keep category ids aligned with the directory structure.

## Sample YAML Rules

Supported sample fields:

- `id`: stable unique sample id
- `title`: display name
- `description`: short summary shown in Explore
- `thumbnail`: optional image path/url or `null`
- `video`: optional video path/url or `null`
- `video_prompt`: optional prompt string used by the explore-showcase skill to generate a video for this showcase (not shown in UI)
- `tutorial`: optional media path/url or webpage url
- `tutorial_prompt`: optional prompt string used by the explore-showcase skill to generate an online interactive tutorial (not shown in UI)
- `request`: optional requirement/reference media or webpage url
- `prompt`: starter prompt text
- `workflow`: optional workflow path
- `directory`: optional directory path
- `git_tag`: git tag string or `null`
- `use_worktree`: boolean
- `in_mode`: `dev` or `prod`
- `skills`: array
- `extensions`: optional array
- `tools`: array
- `files`: array
- `goals`: optional markdown list string describing the expected outcomes after the user completes the showcase task
- `zip-files-url`: optional URL to a zip file that is auto-unzipped to `workspace/showcases/{id}/` when the user starts the template


- `terms`: optional string array of technology terms related to this showcase; users can click each term to learn more
- `related`: optional array of `{ slug, caption }` entries where `slug` references another showcase `id` and `caption` explains why it is related
- `variants`: optional array of `{ slug, caption }` entries where `slug` references another showcase `id` and `caption` explains how a similar prompt produces a meaningfully different result
- `links`: array of `{ name, url, prompt }` where `prompt` is optional and used by the explore-showcase skill to generate linked resource content (not shown in UI)
- `popularity`: numeric score
- `level`: numeric difficulty
- `rate`: numeric rating

## Runtime Mode Rules

- `in_mode` controls which instance should be used for the sample.
- Allowed values are `dev` and `prod`.
- If `in_mode` is missing or empty, treat it as `prod`.
- If `in_mode=prod`, execute in the current instance.
- If `in_mode=dev` and the current instance is `dev`, execute and monitor in the current instance.
- If `in_mode=dev` and the current instance is `prod`, execute in the prod web terminal and monitor the result in the dev instance.
- `prod` is the stable working terminal.
- `dev` is the live preview and monitoring instance for `core/webui` and `core/engine` changes.

## Directory Rules

- New samples should set `directory` to a type-based destination plus the sample id/slug.
- Use `workspace/learning/{id}` for learning content, tutorials, courses, lesson plans, assignments, or slides-as-learning-material.
- Use `workspace/research/{id}` for research, analysis, comparison, browser research, notes, reports, or source investigation.
- Use `workspace/tasks/{id}` for operational tasks, cloud setup, local setup, media-generation tasks, and general non-coding tasks.
- Use `workspace/vibe-coding/{id}` for product, app, website, game, or prototype coding work outside Skill Pilot core.
- Use `core/development/{id}` for Skill Pilot core, codeware, `core/webui`, `core/engine`, system skills, or dev-swarm skill development.
- If the type cannot be detected confidently, use `workspace/tasks/{id}`.
- Template files are packaged from `workspace/showcases/{id}/`, but prompts should reference the copied destination path, for example `@workspace/tasks/cloud-setup-aws-credentials/requirements.md`.

## Constraints

- If `git_tag` is set, `use_worktree` must be `true`.
- If `use_worktree` is `true`, `in_mode` must be `dev`.
- Do not add samples that violate those constraints.
- When updating an existing sample to use `git_tag`, also set `use_worktree: true`.
- When updating an existing sample to use `use_worktree`, also set `in_mode: dev`.

## Editing Guidance

- Keep YAML field names consistent across samples.
- Prefer `null` over empty strings for optional scalar fields unless the loader requires otherwise.
- Keep prompts concise but runnable. Use `prompt: |-` for multi-line prompts so file references and instructions are easy to read.
- For `links`, omit `prompt` when `url` is provided. Add `prompt: |-` only when the linked resource needs generated tutorial or video content and no URL already supplies the destination.
- Use repo-relative paths for `workflow`, `directory`, and `files`.
- Keep `extensions` values as extension names or `extensions/...` paths.
- Preserve stable ids; do not rename ids casually because UI routes and references may depend on them.
- When adding a new category or subcategory, create the matching folder path under `showcases/`.
- When removing or renaming folders, update `showcases.json5` in the same change.

## Validation Expectations

- Before finishing edits, check that every category id maps to the expected folder.
- Check that every sample YAML parses cleanly.
- Check that `git_tag` and `use_worktree` samples are marked `in_mode: dev`.
- Keep `showcases.json5` free of explanatory comments; this file is the source of maintenance guidance.
