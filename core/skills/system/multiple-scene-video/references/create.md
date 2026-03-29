# Create Multiple Scene Video

Use this flow when the user wants a brand-new multi-scene video.

Inputs:

- `requirement`: required
- `target_duration`: optional, default `60`
- `resolution`: optional, default `1080x1920`
- `output_path`: optional, default `"/tmp"`

If `requirement` is missing, ask for it before invoking the API.

Command:

```bash
core/bin/api-invoke create_multiple_scene_video '{"requirement":"...", "target_duration":60, "resolution":"1080x1920", "output_path":"/tmp"}'
```

API:

- `POST /api/create_multiple_scene_video`

Expected success response:

```json
{"video_file_path":"<generated-path>"}
```

If the command fails, report the exact error and include the payload values used.
