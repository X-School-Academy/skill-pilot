# Resume Multiple Scene Video

Use this flow when the user wants to resume, recover, or rebuild an existing multi-scene video run.

Inputs:

- `output_path`: required and must point to the existing workflow output directory

Command:

```bash
core/bin/api-invoke resume_multiple_scene_video '{"output_path":"/tmp/video-run"}'
```

API:

- `POST /api/resume_multiple_scene_video`

Behavior:

- The workflow scans the saved state and scene plan under `output_path`
- Missing dependent files cause the related scene video and final video to be regenerated
- If all required files already exist, the workflow returns without rebuilding anything

Expected success response:

```json
{"video_file_path":"<generated-path>"}
```

If the command fails, report the exact error and include the `output_path` used.
