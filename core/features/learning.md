# Learning

## Brief

Course and lesson workspace for browsing learning files, editing content, previewing markdown, and generating course material.

## User Value

- Centralizes structured learning content in one workspace.
- Supports iterative course authoring and review.
- Connects the UI to course-generation workflows.

## Main Behavior

- Loads the course tree from the learning workspace.
- Opens the latest or selected learning file.
- Supports markdown editing and preview.
- Can reset or save course content.
- Uses course-creation prompts to drive new learning material generation.

## Related Features

- `platform-shell-and-navigation.md`
- `tasks.md`
- `skills-management.md`

## Code References

- `core/webui/pages/courses/index.tsx`
- `core/engine/routes.py`
- `core/engine/course_manager.py`
- Keywords: `CoursesPage`, `buildCourseCreatorPrompt`, `fetchTree`, `fetchContent`, `fetchLatest`, `course-creator`
- API routes: `/api/courses/tree`, `/api/courses/latest`, `/api/courses/content`, `/api/courses/reset`, `/api/courses/save`

