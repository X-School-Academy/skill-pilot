# Feature Retrieval Index: Live Avatar

## Retrieval Keywords

live avatar, live-avatar, avatar, MuseTalk, talking head, avatar config, live_avatar, live-avatar page, avatar service, avatar extension, musetalk_cli, live avatar config, webcam avatar

## Scope

- Live avatar configuration and rendering
- MuseTalk-based talking head generation
- Avatar page in the web UI
- Excludes: cameras/WebRTC (see `cameras-webrtc.md`), media MCP (see `media-mcp-server.md`)

## Main Behavior

- `GET /api/live-avatar/config` returns live avatar service configuration
- Avatar rendering driven by MuseTalk model
- Configuration read from `config/settings.json5` under `services.live_avatar`
- Web UI page at `/live-avatar`

## Code Map

- `core/engine/routes_integrations.py` — `GET /api/live-avatar/config` handler
- `core/engine/settings.py` — `_read_service_config("live_avatar", ...)` helper
- `core/engine/mcp_servers/media/external_scripts/musetalk_cli.py` — MuseTalk CLI
- `core/webui/pages/live-avatar/index.tsx` — live avatar web UI page
- `extensions/live-avatar/` — live avatar extension
- `.skillpilot/temp/MuseTalk/` — MuseTalk model temp directory

## Search Commands

```bash
rg "live.avatar" core/engine/routes_integrations.py -n
rg "live_avatar" core/engine/settings.py -n
find extensions/live-avatar/ -type f
cat core/webui/pages/live-avatar/index.tsx | head -30
```

## Related Features

- `core/features/media-mcp-server.md`
- `core/features/cameras-webrtc.md`
- `core/features/tts-audio-service.md`

## Update Notes

- MuseTalk model files are in `.skillpilot/temp/MuseTalk/` (gitignored)
- `services.live_avatar.server_url` in `settings.json5` must point to the running avatar service
