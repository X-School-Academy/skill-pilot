---
name: explore-showcase
description: Create or update Skill Pilot Explore showcase entries
---

# AI Builder - Explore Showcase

Create and publish Skill Pilot showcase entries — from concept to published data and assets.

## When to Use This Skill

- The user wants to draft a new Explore showcase entry from an idea or a reference project.
- The user wants to generate the thumbnail, video, or interactive tutorial assets for a showcase.
- The user wants to publish an approved showcase to `core/engine/data/showcases/` and copy its assets to `core/webui/public/showcases/`.
- The user wants to create a reverse-engineering showcase (Skill Pilot feature, project, or game) tied to a `git_tag` if needed.

## Your Roles in This Skill

- **Product Manager**: Frame the audience, the "Do first, learn afterwards" outcome, and pick the right showcase type.
- **Technical Writer**: Draft `showcase.yaml`, `goals`, `terms`, `requirements.md`, `update.md`, or `issues.md`.
- **Creative Strategist**: Shape the thumbnail, video, and tutorial prompts so the assets fit the target audience.
- **Backend Developer**: Wire the published YAML into `core/engine/data/showcases/{category}/` and update `showcases.json5` if needed.
- **QA Engineer**: Validate that the YAML parses, the `git_tag` / `use_worktree` / `in_mode` constraints hold, and the assets resolve.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow the three-step workflow below (Draft → Generate Assets → Publish). Ask for user review and approval at the end of steps 1 and 2 before continuing. The remaining sections describe the audience, showcase types, and content schema you must follow.

## Audiences

This project serves four audiences:

1. **AI agent learners** — learning how to use AI agents to solve problems.
2. **AI agent builders** — learning how to build AI agents.
3. **Job seekers** — deepening knowledge of AI agent technology and traditional software development to enter the AI agent industry.
4. **Business owners** — wanting to use AI agents to run an AI-native business.

The concept is **"Do first, learn afterwards."** Showcases give users a ready-made prompt or template to do something with AI first, then explore the underlying knowledge only when they need it.

## Showcase Categories and Types

Every showcase belongs to exactly one **category**, and within that category to a specific **type**. The category determines the audience focus and subject domain; the type defines the recurring shape of the showcase (what the user starts with, what the agent does, what the user ends up with).

- The canonical category list lives in [references/categories.md](references/categories.md).
- The types available inside each category live in [references/category-types/{category-id}.md](references/category-types/).
- The `id` of each category must match an entry in `core/engine/data/showcases.json5`.

When drafting a new showcase:

1. Open `references/categories.md` and pick the best-fitting category.
2. Open `references/category-types/{category-id}.md` and pick a type within it.
3. If no category fits, propose a new category — add a row to `references/categories.md` AND create `references/category-types/{new-id}.md` AND add the entry to `showcases.json5`.
4. If the category fits but no type does, propose a new type inside the matching `category-types/{category-id}.md`.

The published categories at the time of writing are: `basics`, `browser-tasks`, `tutorials`, `slides`, `websites`, `games`, `media-generation`, `ai-agents`, `agent-skills`, `mcp-servers`, `platform-dev`, `cloud-gpu`, `maths`, `vibe-coding`, and `others`.

`vibe-coding` and `others` are catch-all categories. Only use them when no more specific category fits — `vibe-coding` for coding tasks, `others` for non-coding tasks.

## Content of Each Showcase

Each showcase entry contains:

1. A **thumbnail image** with a title and short description.
2. A **prompt string** for users to guide the AI agent.
3. **Files** packaged for the template, placed at `workspace/showcases/{showcase_slug_id}/`:
   - `requirements.md` (if applicable)
   - `update.md` (if applicable)
   - `issues.md` (if applicable)
   - `assets/` (if applicable)
   - Files can also be provided as a `zip-files-url` that is auto-unzipped to `workspace/showcases/{showcase_slug_id}/` when the user starts the template.
   - If the prompt content is short enough, there may be no separate file — the prompt includes everything directly.
   - User-facing prompt references must use the final copied location, not the packaging location. For example: `Use @workspace/tasks/cloud-setup-aws-credentials/requirements.md`.
4. **Other YAML fields**:
   - `goals`: expected outcomes after the user completes the task (markdown list).
   - `request`: a string content which is used to ask user to do a task as user's manager. When `request` is set, leave the `prompt` field as a blank placeholder so the user drafts it themselves.
   - `git_tag`: git commit or tag (mostly for reverse-engineering showcases; requires `use_worktree: true`).
   - `workflow`: agent workflow to use.
   - `skills`: list **every** agent skill that will be invoked or triggered — directly or transitively — when the user runs the showcase prompt. Include skills that are currently **disabled** as well, since the showcase declares the full set of skills required. To compile this list:
     1. Walk through the prompt mentally and identify each skill the agent must call.
     2. Open each candidate skill's `SKILL.md` and follow its references to nested skills it invokes.
     3. Search `core/skills/` and `dev-swarm/skills/` for partial-name matches when the user mentions a skill by short name.
     4. Add any skill that produces a deliverable named in `goals` or referenced in `tools`.
   - `extensions`: agent extensions to use.
   - `tools`: list every shell command, CLI binary, or executable script used either by the showcase prompt directly or by any skill in `skills`. Examples: `ffmpeg`, `ffprobe`, `pnpm`, `uv`, `core/bin/create-image`, `core/bin/create-audio`. Include project-local scripts with their repo-relative path.
   - `in_mode`: `prod` (execute in the stable prod instance) or `dev` (execute in prod, monitor in dev WebUI for live-reload).
   - `directory`: where the files will be copied to from the showcase files folder `workspace/showcases/{showcase_slug_id}/` when using the template. Always set it to a type-based directory plus the showcase id/slug, using the rules in "Directory Selection" below.
   - `terms`: every technology, format, protocol, or concept knowledge that is related to the showcase outcome, the listed `tools`, or any skill in `skills`. Cover language/runtime terms (e.g., `python`, `bash`, `uv`, `pip`), formats (`mp3`, `wav`, `png`, `mp4`, `yaml`, `json`, `markdown`), codecs/parameters (`h264`, `x264`, `h264 CRF`, `yuv420p`, `fps`, `bitrate`), tooling concepts (`ffmpeg filter`, `shell command`, `bash script`, `apt-get`, `brew`), and model names used (`gpt-image-2`, `gpt-4o-mini-tts`). Users explore these terms to learn the knowledge behind the showcase.
   - `related`: optional related showcase list, using `{ slug, caption }` entries where `slug` is another showcase id and `caption` explains the connection.
   - `variants`: optional variant showcase list, using `{ slug, caption }` entries where `slug` is another showcase id and `caption` explains how a similar prompt creates a different result.
   - `video_prompt`: a prompt used to generate a short video that either (a) teaches what the user will learn from running the showcase, or (b) demos the final result the showcase produces. Prefer the demo angle for media/visual showcases and the learning angle for skill/concept showcases. Write it as creative direction for a video generator: subject, scenes, pacing, narration tone, and the final takeaway.
   - `tutorial_prompt`: a prompt used to generate a tutorial video or an online interactive course that walks the user through completing this specific showcase end-to-end. It should describe the audience, the lesson arc (setup → guided steps → final result), the checkpoints, and what the learner can run themselves.
   - `links[].prompt`: each entry under `links` is a related knowledge topic (e.g., `Bash`, `Python vs uv`, `markdown/yaml/json`) drawn from `terms`. Its `prompt` is used to generate a tutorial video or an online interactive course **about that underlying knowledge**, not about the showcase itself. Scope each prompt to one topic so it stays reusable across showcases that share the same term. If the link already has a `url`, omit `prompt`; the URL is enough and no generated tutorial prompt data is needed.

## Directory Selection

Every showcase must set `directory` to one of these base directories plus the showcase id/slug:

| Showcase shape | Directory |
|---|---|
| Learning content, tutorials, courses, lesson plans, assignments, slides-as-learning-material | `workspace/learning/{showcase_slug_id}` |
| Research, analysis, comparison, browser research, notes, reports, source investigation | `workspace/research/{showcase_slug_id}` |
| Operational tasks, cloud setup, local setup, media-generation tasks, general non-coding tasks | `workspace/tasks/{showcase_slug_id}` |
| Product/app/site/game/prototype coding work outside Skill Pilot core | `workspace/vibe-coding/{showcase_slug_id}` |
| Skill Pilot core, codeware, `core/webui`, `core/engine`, system skills, or dev-swarm skill development | `core/development/{showcase_slug_id}` |

If the type cannot be detected confidently, fall back to `workspace/tasks/{showcase_slug_id}`.

Keep `workspace/showcases/{showcase_slug_id}/` as the packaging source for `showcase.yaml`, `files.yaml`, assets, and template files. Write the `prompt` as if the template files have already been copied to `directory`, and reference files with `@{directory}/requirements.md`, `@{directory}/update.md`, `@{directory}/issues.md`, or other concrete copied paths.

## Workflow

Follow these three steps in order. Ask for user review and approval after steps 1 and 2 before proceeding.

---

### Step 1 — Draft showcase.yaml

Create the file `workspace/showcases/{showcase_slug_id}/showcase.yaml` with all applicable fields for user review and approval.

The YAML must follow the schema documented in `core/engine/data/AGENTS.md`.
Before writing the `prompt` field, read `references/prompt-writing.md` and follow its user-facing prompt rules.

Key decisions to make for each showcase:
- Choose the correct `in_mode`: `dev` for Skill Pilot development showcases, `prod` for everything else.
- Set `use_worktree: true` and `git_tag` only for reverse-engineering showcases that need a specific code checkpoint.
- Set `directory` using the "Directory Selection" table, always ending with `{showcase_slug_id}`.
- Write a clear, runnable, user-facing `prompt` string. Use YAML block scalar style `prompt: |-` for multi-line prompts. Reference files with their copied destination paths, for example `Use @workspace/tasks/cloud-setup-aws-credentials/requirements.md`.
- Write a `goals` field as a markdown bullet list of expected outcomes.
- Choose `terms` for technology concepts users can explore later.
- Add `related` entries when another showcase is a natural next step or prerequisite; keep captions short and user-facing.
- Add `variants` entries when another showcase uses a similar prompt shape but intentionally changes the outcome, implementation language, skill selection, agent setup, or failure/recovery path; keep captions short and user-facing.
- Write `video_prompt` and `tutorial_prompt` if you plan to generate media assets in step 2.

Ask the user to review and approve `showcase.yaml` before continuing.

---

### Step 2 — Generate assets

After approval, generate the showcase assets using the appropriate agent skills:

| Asset | Skill |
|---|---|
| Thumbnail image | `create-image-audio` |
| Video | `multiple-scene-video` |
| Online interactive tutorial | `course-creator` |

Save all generated files to `workspace/showcases/{showcase_slug_id}/assets/`.

Update `showcase.yaml` with the path or URL for each generated asset:
- `thumbnail`: path to the generated image
- `video`: path to the generated video
- `tutorial`: path or URL to the generated tutorial

Maintain `workspace/showcases/{showcase_slug_id}/files.yaml` listing all files created for this showcase. This list will be used to zip the assets for distribution.

Example `files.yaml`:
```yaml
showcase_id: {showcase_slug_id}
files:
  - path: showcase.yaml
  - path: assets/thumbnail.png
  - path: assets/video.mp4
  - path: assets/tutorial.md
  - path: requirements.md
```

Ask the user to review the generated assets and approve before continuing.

---

### Step 3 — Publish

After user approval:

1. Determine the showcase category folder under `core/engine/data/showcases/`. Create the folder if it does not exist and add it to `core/engine/data/showcases.json5`.
2. Write the final `core/engine/data/showcases/{category}/{showcase_slug_id}.yaml` with the approved content.
3. Copy any asset files (thumbnail, video, tutorial) to `core/webui/public/showcases/{category}/` and update the YAML paths to use the `/showcases/{category}/...` webui public path.
4. Run a quick validation check: ensure the YAML parses cleanly and any `git_tag` + `use_worktree` + `in_mode` constraints are satisfied (see `core/engine/data/AGENTS.md`).
5. Report what was created or updated, and what the user can do next.

## Handling Reverse-Engineering Showcases

For type 11 (Skill Pilot reverse engineering):
- Identify the target feature and the git commit checkpoint.
- Read `references/reverse-engineering-guide.md` for the process.
- Draft `requirements.md` for the feature or skill, placed under `workspace/showcases/{id}/`.
- Set `git_tag` to the checkpoint commit and `use_worktree: true` and `in_mode: dev`.

For type 12 (project / game reverse engineering):
- Accept a project git URL from the user.
- Read `references/from-a-project.md` for the process.
- Draft a `requirements.md` describing the project to re-implement.
- Keep existing assets from the original project; do not regenerate them unless the user requests it.
- Set `assets/` to hold any preserved original assets.
