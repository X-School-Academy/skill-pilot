# Feature Retrieval Index: Course Creator and AI Courses

## Retrieval Keywords

course, course creator, AI course, course planner, course manager, course tree, courses API, course reset, course save, course content, course schedule, learning, interactive course, workspace/learning, schedule-course, course-planner, course_manager, course_utils, course-plan-and-schedule

## Scope

- AI-generated interactive course creation and management
- Course content serving, saving, and resetting via API
- Course planner skill for scheduling course sessions
- Excludes: assignment/learning platform (Strapi-based courses), vibe coding (separate)

## Main Behavior

- `GET /api/courses/tree` returns course directory tree
- `GET /api/courses/latest` returns the most recently active course
- `GET /api/courses/content` returns course content
- `POST /api/courses/reset` resets a course to initial state
- `POST /api/courses/save` saves course content
- Course workflows coordinated by `course-plan-and-schedule.json`

## Code Map

- `core/engine/routes.py` — `/api/courses/*` route handlers
- `core/engine/course_manager.py` — course management logic
- `core/engine/course_utils.py` — course utility functions
- `core/engine/workflow/course_planner.py` — AI course planner
- `core/skills/system/course-creator/` — course creator skill
- `core/skills/system/course-planner/` — course planner skill
- `core/skills/system/schedule-course/` — scheduled course delivery skill
- `core/workflows/course-plan-and-schedule.json` — course workflow template
- `core/webui/pages/courses/index.tsx` — courses web UI page

## Search Commands

```bash
rg "api/courses" core/engine/routes.py -n
find core/skills/system/course-creator/ -type f
find core/skills/system/course-planner/ -type f
rg "course_manager" core/engine/ -l
```

## Related Features

- `core/features/assignment-learning-platform.md`
- `core/features/workflow-runner-editor.md`
- `core/features/skill-agent-system.md`

## Update Notes

- Courses differ from assignments: courses are locally generated; assignments are Strapi-backed
- `workspace/learning/` is suggested starting point for users; may store course notes
