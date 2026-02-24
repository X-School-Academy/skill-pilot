# Kill Pilot Chrome Extension

This extension adds a `Kill Pilot` context menu item to webpages and sends tasks to the local webui Socket.IO backend.

## Tech Setup

- Package manager: npm
- Dependencies:
  - `socket.io-client`
  - `dotenv`
- Build tool:
  - `esbuild` (via `npm run build`)

## File Layout

- Source code: `chrome-extension/src/`
- Build script: `chrome-extension/scripts/build.mjs`
- Environment file: `chrome-extension/.env`
- Output folder: `chrome-extension/dist/`

## Environment

Set values in `chrome-extension/.env`:

```env
SOCKET_SERVER_URL=http://127.0.0.1:3001
LOCAL_CHROME_TOKEN=YOUR_LOCAL_CHROME_TOKEN
```

`LOCAL_CHROME_TOKEN` must match `webui/.env`.

## Local Setup Guide

1. Build the extension assets:

```bash
cd chrome-extension
npm install
npm run build
```

2. Start webui server:

```bash
cd webui
uv run python main.py
```

3. Open Chrome and go to `chrome://extensions`.
4. Enable `Developer mode`.
5. Click `Load unpacked`.
6. Select `chrome-extension/dist/`.

## Local Test

1. Open any webpage.
2. Optionally select text.
3. Right-click and choose `Kill Pilot`.
4. Enter a task description and submit.
5. In extension service worker logs, verify:
   - socket connect + sign-in response
   - `kill-pilot-task` send log
   - backend ack event (`kill-pilot-task-received`)
