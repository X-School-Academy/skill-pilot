# Security Cameras

## Brief

Camera operations screen for discovering cameras, configuring streams, and handling WebRTC-based viewing and control.

## User Value

- Consolidates camera setup and monitoring in one UI.
- Supports both discovery and manual configuration paths.
- Connects camera control to realtime viewing and server-side signaling.

## Main Behavior

- Fetches camera configuration and renders the camera list.
- Supports ONVIF discovery and manual camera addition.
- Opens settings and delete flows for existing cameras.
- Creates WebRTC offers and answers for camera sessions.
- Exchanges signaling and camera control events through API and data-channel flows.

## Related Features

- `live-avatar.md`
- `extensions.md`

## Code References

- `core/webui/pages/cameras/index.tsx`
- `core/engine/routes.py`
- `core/engine/mcp_servers/cameras`
- `core/skills/system/cameras-webrtc-offer/SKILL.md`
- `core/skills/system/cameras-webrtc-ice-candidate/SKILL.md`
- Keywords: `CamerasPage`, `startDiscovery`, `createOffer`, `createAnswer`, `dcSend`, `delete_camera`, `camera_deleted`
- API routes: `/api/cameras/config`, `/api/cameras/signal`

