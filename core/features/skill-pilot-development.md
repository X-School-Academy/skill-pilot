# Skill Pilot Development

## Brief

Feature-oriented development workspace for creating product feature requests under `core/development` and running the dedicated feature lifecycle skills.

## User Value

- Aligns development work around reusable product features instead of generic projects.
- Tracks related feature references when creating new work.
- Uses a dedicated feature lifecycle from refine through merge.

## Main Behavior

- Lists existing development feature folders and existing frozen features from `core/features`.
- Creates a new feature folder or creates an update or issue request for an existing feature.
- Appends related feature references into created request files.
- Exposes action buttons such as `Refine`, `Initial`, `Plan`, `Implement`, `Review`, `Test`, `Merge`, `Update Code`, and `Fix Issues`.
- Runs either a selected feature skill or a selected workflow against the active development file.

## Related Features

- `vibe-coding.md`
- `workflows.md`
- `skills-management.md`

## Code References

- `core/webui/pages/skill-pilot-development/index.tsx`
- `core/engine/routes.py`
- `core/skills/system/skill-pilot-feature-create/SKILL.md`
- `core/skills/system/skill-pilot-feature-refine/SKILL.md`
- `core/skills/system/skill-pilot-feature-initial/SKILL.md`
- `core/skills/system/skill-pilot-feature-plan/SKILL.md`
- `core/skills/system/skill-pilot-feature-implement/SKILL.md`
- `core/skills/system/skill-pilot-feature-review/SKILL.md`
- `core/skills/system/skill-pilot-feature-test/SKILL.md`
- `core/skills/system/skill-pilot-feature-merge/SKILL.md`
- `core/skills/system/skill-pilot-feature-update/SKILL.md`
- `core/skills/system/skill-pilot-feature-fix-issues/SKILL.md`
- Keywords: `SkillPilotDevelopmentPage`, `fetchFeatureOptions`, `createEntry`, `createFeatureRequest`, `selectedRelatedFeatures`, `fileActions`
- API routes: `/api/skill-pilot-development/features`, `/api/skill-pilot-development/tree`, `/api/skill-pilot-development/latest`, `/api/skill-pilot-development/content`, `/api/skill-pilot-development/save`, `/api/skill-pilot-development/create-feature`, `/api/skill-pilot-development/create-update-request`, `/api/skill-pilot-development/create-issue-report`, `/api/skill-pilot-development/delete`, `/api/skill-pilot-development/file`

