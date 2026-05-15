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

## Showcase Types

The thirteen types of showcases users can do with Skill Pilot AI agents:

1. **Browser tasks** — search, set up tokens from a website, AWS web console operations, etc.
2. **MCP / CLI tool tasks** — git operations, AWS, RunPod instance management, etc.
3. **Content creation** — videos, audio books, educational or social media content (YouTube, TikTok, etc.).
4. **Document creation** — slides, spreadsheets, documents for work or education.
5. **Interactive tutorials** — online self-paced learning experiences.
6. **Vibe coding** — build a small project without coding knowledge: website, game, mobile app, MCP server, agent skill, npm/pip package, etc.
7. **Research** — technical research, market research, etc.
8. **Automation tasks** — calendar management, email management, scheduled agents, etc.
9. **Remote control via Discord bot** — control agents remotely, receive status notifications, human-in-the-loop approvals.
10. **Skill Pilot development** — create new skills, update UI, add extensions, fix bugs, etc.
11. **Reverse engineering (Skill Pilot)** — remove a feature or introduce a bug, draft a `requirements.md`, then ask users to implement it.
12. **Reverse engineering (project / game)** — provide a git URL, draft a `requirements.md`, keep assets, ask users to re-implement from scratch.
13. **Codeware tasks** — check update, code restore, make contribution, create documentation, learn license and compliance.

## Content of Each Showcase

Each showcase entry contains:

1. A **thumbnail image** with a title and short description.
2. A **prompt string** for users to guide the AI agent.
3. **Files** referenced in the prompt, placed at `workspace/showcases/{showcase_slug_id}/`:
   - `requirements.md` (if applicable)
   - `update.md` (if applicable)
   - `issues.md` (if applicable)
   - `assets/` (if applicable)
   - Files can also be provided as a `zip-files-url` that is auto-unzipped to `workspace/showcases/{showcase_slug_id}/` when the user starts the template.
   - If the prompt content is short enough, there may be no separate file — the prompt includes everything directly.
4. **Other YAML fields**:
   - `goals`: expected outcomes after the user completes the task (markdown list)
   - `request`: a string content which is used to ask user to do a task as user's manager, in this case, leave the `prompt` field as a blank placeholder, asking the user to draft it themselves
   - `git_tag`: git commit or tag (mostly for reverse-engineering showcases; requires `use_worktree: true`)
   - `workflow`: agent workflow to use
   - `skills`: agent skills to use
   - `extensions`: agent extensions to use
   - `tools`: additional tools (e.g., ffmpeg)
   - `in_mode`: `prod` (execute in the stable prod instance) or `dev` (execute in prod, monitor in dev WebUI for live-reload)
   - `directory`: where the files will be copied to from the showcase files folder `workspace/showcases/{showcase_slug_id}/` when use template
   - `terms`: technology terms users can explore afterwards
   - `video_prompt`: prompt used to generate the showcase video
   - `tutorial_prompt`: prompt used to generate the online interactive tutorial or video
   - `links[].prompt`: prompt used to generate interactive tutorials or videos

## Workflow

Follow these three steps in order. Ask for user review and approval after steps 1 and 2 before proceeding.

---

### Step 1 — Draft showcase.yaml

Create the file `workspace/showcases/{showcase_slug_id}/showcase.yaml` with all applicable fields for user review and approval.

The YAML must follow the schema documented in `core/engine/data/AGENTS.md`.

Key decisions to make for each showcase:
- Choose the correct `in_mode`: `dev` for Skill Pilot development showcases, `prod` for everything else.
- Set `use_worktree: true` and `git_tag` only for reverse-engineering showcases that need a specific code checkpoint.
- Set `directory` when the showcase files belong somewhere other than `workspace/showcases/{id}/` (e.g., `core/development/{feature}/` for codeware showcases).
- Write a clear, runnable `prompt` string. Reference files with `@path/to/file`.
- Write a `goals` field as a markdown bullet list of expected outcomes.
- Choose `terms` for technology concepts users can explore later.
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
