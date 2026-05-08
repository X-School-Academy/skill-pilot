# Vibe Coding

## Brief

Project-oriented coding workspace for creating projects, capturing change requests, and running implementation skills or workflows against project files.

## User Value

- Keeps requirements, requests, issues, and lifecycle records inside each project's `design-docs/` folder.
- Makes the project lifecycle explicit from refine through deploy.
- Supports mixed file types, not just markdown.

## Main Behavior

- Creates `workspace/vibe-coding/{project-name}/design-docs/requirements.md` for new projects.
- Creates update requests and issue reports as `design-docs/update.md` and `design-docs/issues.md`.
- Opens files for editing or media preview depending on type.
- Exposes action buttons such as `Refine`, `Initial`, `Plan`, `Implement`, `Review`, `Test`, `Deploy`, `Update Code`, and `Fix Issues`.
- Runs either a selected skill or a selected workflow against the current instruction file.

## Related Features

- `tasks.md`
- `research.md`
- `skill-pilot-development.md`
- `workflows.md`

## Code References

- `core/webui/pages/vibe-coding/index.tsx`
- `core/engine/routes.py`
- `core/skills/system/vibe-coding-project-refine/SKILL.md`
- `core/skills/system/vibe-coding-project-initial/SKILL.md`
- `core/skills/system/vibe-coding-project-plan/SKILL.md`
- `core/skills/system/vibe-coding-project-implement/SKILL.md`
- `core/skills/system/vibe-coding-project-review/SKILL.md`
- `core/skills/system/vibe-coding-project-test/SKILL.md`
- `core/skills/system/vibe-coding-project-deploy/SKILL.md`
- `core/skills/system/vibe-coding-project-update/SKILL.md`
- `core/skills/system/vibe-coding-project-fix-issues/SKILL.md`
- Keywords: `VibeCodingPage`, `createProject`, `createProjectRequest`, `fileActions`, `runAction`
- API routes: `/api/vibe-coding/tree`, `/api/vibe-coding/latest`, `/api/vibe-coding/content`, `/api/vibe-coding/save`, `/api/vibe-coding/create-project`, `/api/vibe-coding/create-update-request`, `/api/vibe-coding/create-issue-report`, `/api/vibe-coding/delete`, `/api/vibe-coding/file`
