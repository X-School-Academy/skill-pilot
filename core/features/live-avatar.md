# Live Avatar

## Brief

Interactive live-avatar screen for connecting to a realtime avatar server over WebRTC.

## User Value

- Gives users a real-time avatar interaction surface from the WebUI.
- Connects browser media and signaling to the backend avatar service.
- Exposes connection status directly in the UI.

## Main Behavior

- Loads the live-avatar configuration from the backend.
- Creates a WebRTC offer and negotiates a peer connection.
- Handles connection errors and server availability issues.
- Uses the retrieved config to set up the client session.

## Related Features

- `new-session.md`
- `ai-and-security.md`

## Code References

- `core/webui/pages/live-avatar/index.tsx`
- `core/engine/routes.py`
- Keywords: `LiveAvatarPage`, `createOffer`, `pc`, `setStatusMsg`, `Connection failed`
- API routes: `/api/live-avatar/config`

