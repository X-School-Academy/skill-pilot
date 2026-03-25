# API Invoke Reference

Use this exact command shape:

```bash
core/bin/api-invoke create_cpu_video '{"requirement":"...", "target_duration":60, "resolution":"1080x1920"}'
```

Payload fields:

- `requirement`: required string
- `target_duration`: optional integer, default `60`
- `resolution`: optional string, default `1080x1920`

Behavior notes:

- The command talks to the engine through the engine socket.
- The target API is `POST /api/create_cpu_video`.
- The command prints JSON on success.
- If the API returns an error, the command exits non-zero and prints the failure reason.

Response shape:

```json
{"video_file_path":"<generated-path>"}
```
