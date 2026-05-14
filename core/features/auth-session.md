# Feature Retrieval Index: Auth and Session Management

## Retrieval Keywords

auth, authentication, auth status, session, local dev token, API token, server token, apiServerToken, api-server-token, auth session, login, token validation, LOCAL_DEV_TOKEN, session_agent_store, socket_service, heartbeat

## Scope

- Authentication status check and session creation
- Local dev token for development access
- API server token management
- Session agent store for active agent sessions
- Heartbeat mechanism for session keep-alive
- Excludes: user profile (see config-settings), Discord auth (separate)

## Main Behavior

- `GET /api/auth/status` checks if the current request is authenticated
- `POST /api/auth/session` creates or validates an auth session
- `GET /api/local-dev-token` returns the local development token
- `POST /api/heartbeat` keeps a session alive; used by the web UI
- `apiServerToken` feature in webui manages the API server token state

## Code Map

- `core/engine/routes_integrations.py` — `GET /api/auth/status`, `POST /api/auth/session`
- `core/engine/routes.py` — `GET /api/local-dev-token`, `POST /api/heartbeat`
- `core/engine/session_agent_store.py` — in-memory agent session store
- `core/engine/socket_service.py` — WebSocket/Socket.IO session service
- `core/webui/features/apiServerToken/apiServerSlice.ts` — Redux slice for API token
- `core/webui/features/user/userSlice.ts` — Redux slice for user state

## Search Commands

```bash
rg "api/auth" core/engine/routes_integrations.py -n
rg "heartbeat" core/engine/routes.py -n
cat core/engine/session_agent_store.py | head -40
rg "apiServerToken" core/webui/ -l
```

## Related Features

- `core/features/config-settings-mcp-skills.md`
- `core/features/engine-backend-fastapi.md`

## Update Notes

- `LOCAL_DEV_TOKEN` is generated at engine start; rotate by restarting the engine
- Heartbeat interval is managed by the web UI; default is 30 seconds
- `session_agent_store` is in-memory; sessions are lost on engine restart
