# Research

## Brief

Topic-based research workspace for capturing research requirements, refining them, and running research skills or workflows.

## User Value

- Keeps each research topic in its own folder.
- Supports a simple refine-then-research flow.
- Reuses the same execution model as other workspaces.

## Main Behavior

- Creates a topic folder and requirement file in kebab-case.
- Loads research files and previews markdown or media content.
- Supports deletion of the full topic folder from a selected file.
- Offers action buttons for refining a requirement or running deep research.
- Runs either a selected skill or a selected workflow against the active research file.

## Related Features

- `tasks.md`
- `vibe-coding.md`
- `workflows.md`

## Code References

- `core/webui/pages/research/index.tsx`
- `core/engine/routes.py`
- `core/skills/system/refine-research-requirement/SKILL.md`
- `core/skills/system/deep-research/SKILL.md`
- Keywords: `ResearchPage`, `createTopic`, `openExecuteModal`, `runAction`, `fileActions`
- API routes: `/api/research/tree`, `/api/research/latest`, `/api/research/content`, `/api/research/save`, `/api/research/create-topic`, `/api/research/delete`, `/api/research/file`

