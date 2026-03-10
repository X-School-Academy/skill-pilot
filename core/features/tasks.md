# Tasks

## Brief

General-purpose task workspace for creating task files, editing them directly, and executing them with a skill or workflow.

## User Value

- Provides a lightweight workspace when the task does not need a specialized page.
- Supports mixed file types and arbitrary folder structure under the tasks workspace.
- Handles workflow resume checks before execution.

## Main Behavior

- Creates task files in a selected folder or top level.
- Opens text, markdown, image, audio, and video files with the right viewer mode.
- Saves edits and can pass reference files into execution prompts.
- Runs a selected skill or workflow against the current task file.
- Supports next-node trigger selection and workflow resume detection.

## Related Features

- `new-session.md`
- `research.md`
- `vibe-coding.md`
- `workflows.md`

## Code References

- `core/webui/pages/tasks/index.tsx`
- `core/engine/routes.py`
- Keywords: `TasksPage`, `createTask`, `saveCurrentTaskContent`, `runExecuteAction`, `selectedReferenceFiles`, `executeNextNodeTrigger`
- API routes: `/api/tasks/tree`, `/api/tasks/latest`, `/api/tasks/content`, `/api/tasks/save`, `/api/tasks/create`, `/api/tasks/delete`, `/api/tasks/file`

