# Feature Retrieval Index: Cameras and WebRTC

## Retrieval Keywords

cameras, camera, WebRTC, camera config, camera manager, human detection, detection, webrtc_service, camera_manager, cameras MCP, cameras page, camera session, live camera, video stream, face detection

## Scope

- Camera listing and configuration
- WebRTC session management for live video streaming
- Human detection integration
- Camera MCP server for AI agent access
- Excludes: live avatar (separate feature), media MCP (separate feature)

## Main Behavior

- `GET /api/cameras/config` returns camera configuration and available devices
- Camera streams delivered via WebRTC
- Human detection available via `detection.py`
- Camera MCP server exposes camera tools to AI agents

## Code Map

- `core/engine/routes_integrations.py` — `GET /api/cameras/config` handler
- `core/engine/mcp_servers/cameras/` — Camera MCP server: `main.py`, `camera_manager.py`, `detection.py`, `webrtc_service.py`, `tools.py`
- `core/engine/settings.py` — `_read_service_config("cameras", ...)` helper
- `core/webui/pages/cameras/index.tsx` — cameras web UI page

## Search Commands

```bash
rg "api/cameras" core/engine/routes_integrations.py -n
find core/engine/mcp_servers/cameras/ -type f
cat core/engine/mcp_servers/cameras/main.py | head -30
```

## Related Features

- `core/features/live-avatar.md`
- `core/features/media-mcp-server.md`
- `core/features/mcp-terminal-server.md`

## Update Notes

- WebRTC requires STUN/TURN server configuration in `settings.json5` for non-local use
- Human detection requires `requirements-human-detection.txt` dependencies installed
- Camera MCP server runs independently from the main engine
