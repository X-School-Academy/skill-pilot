---
name: explore-showcase
description: Create or update Skill Pilot Explore showcase entries
---

# AI Builder - Explore Showcase

Create and publish Skill Pilot showcase entries — from concept to published data and assets.

## When to Use This Skill

- The user wants to draft a new Explore showcase entry from an idea or a reference project.
- The user wants to generate the thumbnail, video, or interactive tutorial assets for a showcase.
- The user wants to publish an approved showcase to `core/engine/data/showcases/` and publish its public assets through the S3/CloudFront CLI.
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
   - Runtime deliverables such as `output.md`, `user-manual.md`, reports, or generated docs should usually be named in the prompt or requirements file, but not pre-created as packaged template files. Only include a prefilled template for those deliverables when the user explicitly asks for one or the starter content is genuinely necessary.
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
   - `subagents`: optional list of Skill Pilot subagents that should be available or intentionally used when the user runs the showcase prompt. Use this for role-specialized reviewers, researchers, writers, implementation agents, or workflow agents that are not agent skills. To compile this list:
     1. Walk through the prompt and expected workflow to identify role-specialized agents the task naturally needs.
     2. Search `core/subagents/system/` and `core/subagents/user/` for partial-name matches when the user mentions a subagent by short name.
     3. Include disabled subagents too, because the showcase declares the full set of subagents required.
     4. Do not duplicate agent skills here; keep agent skills in `skills` and subagents in `subagents`.
   - `extensions`: agent extensions to use.
   - `tools`: list every shell command, CLI binary, or executable script used either by the showcase prompt directly, by any skill in `skills`, or by any subagent in `subagents`. Examples: `ffmpeg`, `ffprobe`, `pnpm`, `uv`, `core/bin/create-image`, `core/bin/create-audio`, `core/bin/agent-cli`, `core/bin/aws-s3`. Include project-local scripts with their repo-relative path.
   - `in_mode`: `prod` (execute in the stable prod instance) or `dev` (execute in prod, monitor in dev WebUI for live-reload).
   - `directory`: where the files will be copied to from the showcase files folder `workspace/showcases/{showcase_slug_id}/` when using the template. Always set it to a type-based directory plus the showcase id/slug, using the rules in "Directory Selection" below.
   - `terms`: every technology, format, protocol, agent pattern, or concept knowledge that is related to the showcase outcome, the listed `tools`, any skill in `skills`, or any subagent in `subagents`. Cover language/runtime terms (e.g., `python`, `bash`, `uv`, `pip`), formats (`mp3`, `wav`, `png`, `mp4`, `yaml`, `json`, `markdown`), codecs/parameters (`h264`, `x264`, `h264 CRF`, `yuv420p`, `fps`, `bitrate`), tooling concepts (`ffmpeg filter`, `shell command`, `bash script`, `apt-get`, `brew`), agent concepts (`subagent`, `code review`, `multi-agent workflow`), and model names used (`gpt-image-2`, `gpt-4o-mini-tts`). Users explore these terms to learn the knowledge behind the showcase.
   - `previous_showcase`: optional `{ slug_id, title }` object for the immediate prerequisite or previous step in a serial showcase. Use it only when the current showcase may depend on the previous showcase's result.
   - `next_showcase`: optional `{ slug_id, title }` object for the immediate follow-up or next step in a serial showcase.
   - `related`: optional related showcase list, using `{ slug, caption }` entries where `slug` is another showcase id and `caption` explains the connection.
   - `variants`: optional variant showcase list, using `{ slug, caption }` entries where `slug` is another showcase id and `caption` explains how a similar prompt creates a different result.
   - `video_prompt`: a prompt used to generate a short video that either (a) teaches what the user will learn from running the showcase, or (b) demos the final result the showcase produces. Prefer the demo angle for media/visual showcases and the learning angle for skill/concept showcases. Write it as creative direction for a video generator: subject, scenes, pacing, narration tone, and the final takeaway.
   - `tutorial_prompt`: a prompt used to generate a tutorial video or an online interactive course that walks the user through completing this specific showcase end-to-end. It should describe the audience, the lesson arc (setup -> guided steps -> final result), the checkpoints, what the learner can run themselves, and the intended course type when it matters (`guided_challenge` or `interactive_tutorial`). If the course type cannot be detected, the course generator defaults to `guided_challenge`.
   - `links`: optional external references or generated-learning prompts for underlying knowledge topics. Use `url` for existing authoritative references. Use `prompt` only when the showcase should generate an extra tutorial video or online interactive course for a single reusable topic. Link prompts may request either a tutorial video or a markdown course; for markdown courses, state the course type when it matters. Do not put both `url` and `prompt` on the same link unless there is a specific reason to augment an external reference with generated learning content.

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
When writing `requirements.md`, `update.md`, or `issues.md`, do not include much tech detail. Treat the request as coming from a non-tech user — capture what the user wants to do or have, and what problem they have seen from the UI, logs, or unexpected behavior. Do not add generic agent-safety reminders or agent operating policy to these user-authored files, such as prompt-injection warnings before opening websites; those belong in the relevant agent skill behavior and runtime plan.

Key decisions to make for each showcase:
- Choose the correct `in_mode`: `dev` for Skill Pilot development showcases, `prod` for everything else.
- Set `use_worktree: true` and `git_tag` only for reverse-engineering showcases that need a specific code checkpoint.
- Set `directory` using the "Directory Selection" table, always ending with `{showcase_slug_id}`.
- Write a clear, runnable, user-facing `prompt` string. Use YAML block scalar style `prompt: |-` for multi-line prompts. Reference files with their copied destination paths, for example `Use @workspace/tasks/cloud-setup-aws-credentials/requirements.md`. If `requirements.md`, `update.md`, or `issues.md` already defines the details, do not repeat those details in `prompt`; summarize the outcome and point to the file.
- For ordered serial showcases with dependencies:
  - If the current showcase produces information, configuration, credentials metadata, file paths, decisions, or results that the next showcase needs, write the prompt or `requirements.md` so the agent records the reusable handoff information in `@{directory}/output.md`.
  - Keep `output.md` practical for the next task: include only the values, paths, decisions, commands run, result summaries, and warnings the next showcase needs. Do not ask for secret values to be written into `output.md`; use safe references such as profile names, key names, resource ids, or where the user should retrieve a secret.
  - Do not create a starter `output.md` template when the needed output details are already described in `requirements.md`; let the runtime agent decide the final structure from the completed work.
  - If the current showcase depends on `previous_showcase`, write the prompt or `requirements.md` so the agent reads the previous showcase's copied destination output file. Do not say only "previous task" or "previous showcase" because the runtime agent may not have that memory; state what has already been set up and give the exact path. For example: `The AWS credentials profile has been set up; refer to @workspace/tasks/cloud-setup-aws-credentials/output.md for the AWS profile, region, resource names, and setup notes.`
  - Use copied destination paths, not `workspace/showcases/{showcase_slug_id}/`, for every `output.md` reference.
- For other runtime documentation deliverables such as a user manual, name the required filename and expected purpose in `requirements.md` or the prompt. Do not create a starter manual file unless the user asks for a template.
- Populate `skills` and optional `subagents` separately. Use `skills` for reusable agent capabilities and `subagents` for role-specialized agents such as `code-reviewer`; include a `subagents: []` field only when explicit emptiness improves readability.
- Write a `goals` field as a markdown bullet list of expected outcomes.
- Choose `terms` for technology concepts users can explore later.
- Add `related` entries when another showcase is a natural next step or prerequisite; keep captions short and user-facing.
- Add `variants` entries when another showcase uses a similar prompt shape but intentionally changes the outcome, implementation language, skill selection, agent setup, or failure/recovery path; keep captions short and user-facing.
- Add `previous_showcase` and `next_showcase` only for ordered serial showcases where the previous or next item is part of a sequence. Prefer these fields over `related` when the order matters.
- Add `links` for external references or generated learning content about underlying terms. Prefer external `url` links for canonical documentation; use `prompt` when no URL is provided and the intended output is an extra tutorial video or online interactive course about one reusable topic.
- Write `video_prompt` and `tutorial_prompt`. When writing `tutorial_prompt` or `links[].prompt`, include the course type only when the target format is important; otherwise leave it to `course-creator`, which defaults unknown online interactive tutorial courses to `guided_challenge`.

Ask the user to review and approve `showcase.yaml` before continuing.

---

### Step 2 — Generate assets

After approval, generate the showcase assets with the helper script:

```bash
core/skills/system/explore-showcase/scripts/create-assets.py workspace/showcases/{showcase_slug_id}
```

The script can also be run from an installed skill copy such as `.agent/skills/explore-showcase/scripts/create-assets.py`. It discovers the Skill Pilot repo root from the current directory, the showcase path, or the script location, so pass either an absolute showcase path or a repo-relative path such as `workspace/showcases/{showcase_slug_id}`.

Use `--dry-run` when you want to preview and improve generation prompts before publishing. Dry-run still creates local generated media and the zip file, runs generated tutorial/link prompts, then prints their file locations. It skips S3 uploads and does not update `showcase.yaml`, `files.yaml`, or `core/engine/data/terms.json`.

The script:
- Fails if the showcase folder or `showcase.yaml` is missing.
- Generates a landscape thumbnail from `title`, `description`, and `goals` with `core/bin/create-image`, uploads the generated file directly with `core/bin/aws-s3 upload ... --folder image`, and updates `thumbnail`. The thumbnail is not copied into `assets/` for zip packaging.
- Generates a 5 minute, 1080p landscape showcase video from `title`, `description`, `goals`, and `video_prompt` with `core/bin/api-invoke create_multiple_scene_video`, using `.skillpilot/temp/showcases-{uuid}/` as the video workflow output folder. It uploads the generated video directly with `core/bin/aws-s3 upload ... --folder video` and updates `video`; it does not copy the video into the showcase `assets/` folder.
- Generates `tutorial_prompt` and any `links[].prompt` values by creating a target markdown path under `.skillpilot/temp/showcases-courses/{uuid}.md`, then calling `core/bin/agent-cli` with a wrapper prompt that tells `course-creator` to write the course exactly to that path and output it as `<output-file-path>{path}</output-file-path>`. The script parses the tagged absolute file path, verifies it exactly matches the requested temp path, uploads the markdown course with `core/bin/aws-s3 upload ... --folder course`, updates `tutorial` or `links[].url`, and removes consumed `links[].prompt` values once a URL exists. Generated tutorial/link course files are uploaded from their temp path and are not copied into `assets/`.
- Checks each `terms` entry against `core/engine/data/terms.json`, creating that file if needed. For missing terms, it generates an independent 3 minute, 1080p landscape learning video under `.skillpilot/temp/showcases-{uuid}/`, uploads it to the `video` folder, and records the URL under the lowercase URL-safe term slug. Term videos are not copied into `assets/`.
- Zips the showcase folder contents, uploads the zip with `core/bin/aws-s3 upload ... --folder zip`, and updates `zip-files-url`. Already-uploaded generated media should stay out of the showcase folder so it is not zipped and uploaded again.

Video generation is expected to be long-running. `core/bin/api-invoke create_multiple_scene_video` can take many minutes and may take over an hour for longer videos or slow media providers. Do not treat a quiet terminal as a hang. While it runs:

1. Monitor the asset-generation command session periodically.
2. Check the engine tmux terminal, usually `sp-engine-dev` or `sp-engine-prod`, with a pane capture such as `tmux capture-pane -t sp-engine-dev -p -S -120` or `tmux capture-pane -t sp-engine-prod -p -S -120` when permitted.
3. Look for active progress logs such as scene planning, image generation, TTS, rendering, or muxing. If those logs are advancing, keep waiting.
4. Only report an error when the command exits non-zero, the tmux logs show a concrete failure, or the underlying process is no longer running.
5. If sandboxing blocks tmux or process inspection, ask for permission rather than assuming the generation failed.

Keep only template/source files that should be distributed to the user's workspace under `workspace/showcases/{showcase_slug_id}/`, including `assets/` when the template genuinely needs local source assets. Generated thumbnail, showcase video, tutorial/link media, and term videos are uploaded directly from their generated paths and should not be copied into the showcase folder just for review or packaging.

Maintain `workspace/showcases/{showcase_slug_id}/files.yaml` listing only the packaged files that should be included in the showcase zip. Do not list generated media that already has a public S3/CloudFront URL in `thumbnail`, `video`, `tutorial`, `links[].url`, or `core/engine/data/terms.json`.

Example `files.yaml`:
```yaml
showcase_id: {showcase_slug_id}
files:
  - path: showcase.yaml
  - path: requirements.md
  - path: assets/source-image.png
```

Ask the user to review the generated assets and approve before continuing.

---

### Step 3 — Publish

After user approval:

1. Determine the showcase category folder under `core/engine/data/showcases/`. Create the folder if it does not exist and add it to `core/engine/data/showcases.json5`.
2. Write the final `core/engine/data/showcases/{category}/{showcase_slug_id}.yaml` with the approved content.
3. Ensure any public image, video, or zip asset fields use the CloudFront URLs returned by `core/bin/aws-s3`.
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
