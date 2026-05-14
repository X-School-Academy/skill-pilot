# Feature Retrieval Index: File Manager

## Retrieval Keywords

file manager, files API, file upload, file download, file read, file write, file list, file rename, file delete, file copy, file move, mkdir, file events, SSE, files_info, files_list, files_read, files_write, files_upload, files_rename, files_delete, files_copy, files_move, files_mkdir, files_download, files_events, FileManagerContent

## Scope

- REST API for file system operations on the project workspace
- Server-Sent Events (SSE) stream for file change notifications
- Web UI component for browsing and managing files
- Excludes: vibe-coding and tasks file trees (separate features)

## Main Behavior

- `GET /api/files/info` returns file metadata
- `GET /api/files/list` lists directory contents
- `GET /api/files/read` returns file content
- `POST /api/files/write` saves file content
- `POST /api/files/upload` handles multipart file upload
- `POST /api/files/rename` renames a file or directory
- `POST /api/files/delete` deletes file(s)
- `POST /api/files/copy` and `POST /api/files/move` copy/move items
- `POST /api/files/mkdir` creates a directory
- `GET /api/files/download` streams a file for browser download
- `GET /api/files/events` is an SSE endpoint that pushes file-change events

## Code Map

- `core/engine/routes_file_manager.py` — all file API route handlers
- `core/webui/components/FileManagerContent.tsx` — main file manager UI component
- `core/webui/pages/file-manager/index.tsx` — file manager page

## Search Commands

```bash
rg "api/files" core/engine/routes_file_manager.py -n
rg "FileManagerContent" core/webui/ -l
rg "files_events" core/engine/ -n
```

## Related Features

- `core/features/vibe-coding-project-manager.md`
- `core/features/task-manager.md`

## Update Notes

- Path traversal protection must be preserved in all file routes
- `files_events` is an SSE endpoint; verify `EventSourceResponse` compatibility when upgrading starlette
- Test: `pytest core/engine/tests/` targeting file manager tests
