# Chrome DevTools Reverse-Tunnel Proxy — Plan

End-to-end CDP access to a Chrome instance that sits behind NAT / has no public IP, by tunneling through the public Skill Pilot engine.

## Topology

```
┌────────────────────┐        ┌────────────────────────────┐        ┌─────────────────────┐
│ User machine       │        │ Skill Pilot engine (public)│        │ Chrome host (NAT'd) │
│                    │        │                            │        │                     │
│ agent-browser      │        │  FastAPI :3001/3002        │        │  Chrome :9222 CDP   │
│   --cdp ws://engine│        │   /chrome-proxy?token=…    │◄───────┤  Go proxy (tunnel)  │
│        :9223/…     │───────►│  Bridge listener :9223     │        │   -tunnelURL=…      │
└────────────────────┘        └────────────────────────────┘        └─────────────────────┘
       local user                  Python bridge (new)                   Go proxy (updated)
```

Three components:

1. **Go proxy (updated)** — same binary, two modes selected by `-tunnelURL`.
2. **Python bridge (new, in `core/engine`)** — parks remote tunnels at `/chrome-proxy?token=…`, listens on `127.0.0.1:9223` for local CDP clients, pairs them, relays frames.
3. **Local CDP client** — unchanged. Just points at `ws://engine:9223/devtools/browser/<UUID>`.

## The one piece of protocol on top of WebSocket

CDP requires the upstream Chrome WS URL to include the exact `/devtools/browser/<UUID>` or `/devtools/page/<id>` path. The reverse tunnel can't carry that information transparently because the remote Go has already dialed out before any local user shows up.

Solution: **one control frame per session**, then transparent relay.

```
engine ──► remote Go : TEXT  {"path":"/devtools/browser/<UUID>"}      (first frame only)
engine ◄─► remote Go : TEXT/BINARY frames                              (transparent, both directions)
```

- It is a single text frame, JSON-shaped, sent by the engine immediately after a local client connects.
- The remote Go reads exactly one frame, parses it, dials `targetBase + path`, then enters the same `pipe()` loop already used in forward-proxy mode.
- Everything after that frame is byte-for-byte CDP traffic. No CDP parsing anywhere in the stack.

This is the minimum protocol overhead that still keeps CDP correct. Anything less breaks Chrome's UUID requirement.

## Component 1 — Go proxy update (`extensions/chrome-devtool-proxy/main.go`)

### New flag

```
-tunnelURL string   Optional. If set, run in tunnel-client mode.
                    Example: wss://engine.example.com/chrome-proxy?token=abc123
```

### Mode selection

- **`-tunnelURL` empty** → existing forward-proxy behavior. **Zero logic changes.** Same handler, same flags (`-listenAddr`, `-targetBase`, `-allowIP`).
- **`-tunnelURL` set** → tunnel-client mode. `-listenAddr` and `-allowIP` are ignored (logged as such). `-targetBase` is still required (defaults to `ws://127.0.0.1:9222`).

### Tunnel-client mode behavior

Loop:

1. Dial `tunnelURL` with `websocket.Dialer` (TLS verified by default; add `-insecureSkipVerify` only if needed later — not in v1).
2. On dial failure, log and back off (1s → 2s → 5s → 30s cap, reset on success).
3. On success, read **one** message with `ReadMessage()`. Expect text. Parse as `{"path": "/devtools/..."}`. Reject anything else (close with `CloseProtocolError`).
4. Dial Chrome at `targetBase + path` (reuse existing dialer setup; copy a minimal header set if needed — typically none).
5. Wire pings/pongs and run two `pipe()` goroutines exactly like `proxyWS()` does today.
6. When either side closes, close both, then go back to step 1 (re-park).

### Concurrency / pool

For a single concurrent CDP session, one parked tunnel is enough. To support N concurrent sessions, add:

```
-tunnelPool int     Number of concurrent parked tunnels (default 1)
```

Spawn `tunnelPool` goroutines each running the loop above, all using the same `tunnelURL`. The engine picks any idle parked tunnel per local connect.

### Code shape

- Refactor `proxyWS` so the relay core (the two `pipe()` goroutines + ping/pong handlers) is a function `relay(client, upstream *websocket.Conn)`. Both modes call it.
- Forward mode: `client = upgraded incoming`, `upstream = dial targetBase + r.URL.RequestURI()`.
- Tunnel mode: `client = dialed tunnel`, `upstream = dial targetBase + path-from-control-frame`.
- Keep all existing logging tags (`[client]`, `[upstream]`, `[proxy]`) plus a new `[tunnel]` tag.

### What does NOT change

- `-listenAddr`, `-targetBase`, `-allowIP` flags and their defaults.
- `isAllowed`, `copyHeaders`, `localIP`, signal handling, `ReadHeaderTimeout`, `SetReadLimit(32MB)`.
- Forward-proxy code path is byte-identical to today after the `relay()` extraction.

## Component 2 — Python bridge (`core/engine`)

New module: `core/engine/chrome_proxy.py`. Wired into `app_factory.py` lifespan.

### Config (`config/settings.json5`, under `services.engine`)

```json5
chrome_proxy: {
  enabled: true,
  listen_host: "127.0.0.1",
  listen_port: 9223,
  // Tokens are issued via API (see below). No static token list here.
}
```

### Endpoints

#### `WS /chrome-proxy?token=<token>` (mounted on existing FastAPI app)

- Validates `token` against the in-memory session registry.
- If valid + slot free, accepts the upgrade and **parks** the connection in the registry (token → list of idle parked sockets, supporting the Go `-tunnelPool`).
- If the registry has a waiter (a local 9223 connection arrived first), pair immediately instead of parking.
- Closes with `1008 policy violation` on bad/missing token.

#### `WS 127.0.0.1:9223/<any-path>` (standalone aiohttp server)

- Local CDP client connects with the full Chrome path, e.g. `/devtools/browser/<UUID>`.
- Token is taken from a sticky session — see "Token model" below. v1: single global session, no token in the local URL.
- On connect:
  1. Look up an idle parked tunnel. If none, wait up to N seconds (configurable, default 10s); else 503 / close `1013 try again later`.
  2. Send the control frame `{"path": "<path>"}` to the parked tunnel as a single text message.
  3. Run two relay tasks: `local → tunnel` and `tunnel → local`, forwarding text and binary frames; propagate close codes.
- Optional `GET /` returns `ws proxy is running` (parity with the Go version).

### Token model (v1)

Simplest viable: **one session, one token**, generated at engine startup or by an authenticated API call.

```
POST /api/chrome-proxy/sessions       → { "token": "...", "tunnel_url": "wss://engine/chrome-proxy?token=..." }
GET  /api/chrome-proxy/sessions       → list of active sessions + parked tunnel counts
DELETE /api/chrome-proxy/sessions/{token}
```

These endpoints reuse the existing engine auth (whatever guards `/api/*` today). The remote operator hits this once, copies `tunnel_url`, and starts the Go proxy with `-tunnelURL=<that>`. The token is opaque and sufficiently long (`secrets.token_urlsafe(32)`).

For v1 the local 9223 listener does not require a token — it's bound to `127.0.0.1` only, so anything that can connect already has local access. (If we later want to bind on `0.0.0.0`, we'd add `?token=` enforcement on the 9223 side too. Out of scope for v1.)

### Multi-session

The registry is `dict[token, SessionState]`, where `SessionState` holds:
- `parked: list[WebSocket]` (idle tunnels)
- `active: set[(local_ws, tunnel_ws)]`
- `created_at`, `last_used_at`

To support multiple concurrent users sharing one Chrome host, the operator just runs Go with `-tunnelPool=N`. The engine pulls the next idle parked socket on each local connect.

To support multiple distinct Chrome hosts, create multiple sessions (multiple tokens). v1 routes to a single session by default; if more than one is active, the local listener picks the most recently created (or we add `?token=` to the local URL — punted to v2).

### Lifecycle / cleanup

- On engine shutdown: cancel relay tasks, close all sockets cleanly.
- On tunnel disconnect: drop from `parked`/`active`; existing local user gets close code propagated.
- On local disconnect: close the paired tunnel (one tunnel = one session); remote Go will re-dial to re-park.
- Idle session GC: optional, prune sessions with zero parked + zero active for > 1h.

### Why a separate aiohttp server (not FastAPI) for :9223?

FastAPI/Uvicorn is already serving the engine port. We need a second listener on a different port for local CDP traffic. Running a second Uvicorn would pull in routing we don't want here. A small aiohttp `Application` with one WS handler is ~30 lines and lifecycle-managed by the same `asyncio` loop.

## Component 3 — Operator UX

```
# on Chrome host (NAT'd)
chrome-devtools-proxy \
  -tunnelURL=wss://engine.example.com/chrome-proxy?token=abc123 \
  -targetBase=ws://127.0.0.1:9222 \
  -tunnelPool=2

# on user machine
agent-browser open URL --cdp ws://engine.example.com:9223/devtools/browser/<UUID>
```

Note: `:9223` here is on the **engine**, not the Chrome host. The engine binds it on `127.0.0.1` by default, so the user is either on the engine host or comes in via SSH tunnel / port forwarding. Binding `:9223` on `0.0.0.0` is a follow-up (requires per-connection token enforcement).

## Open questions for review

1. **Token issuance**: using the same static token in `config/.env` as the webui
2. **9223 bind host**: only `127.0.0.1`
3. **Multi-session routing on :9223**: single active session (auto-pick), no token required as listen on 127.0.0.1
4. **Concurrency default**: ship Go with `-tunnelPool=1` (simple) - using simple solution
5. **TLS for self-signed engine certs**: no self-signed support, but support both `ws://` and `wss://` for the tunnel URL.
6. **Should the `/api/chrome-proxy/sessions` endpoints be gated behind a feature flag** - add config at config/settings.json5 to control enable or disable for the bridge service

## Out of scope for this iteration

- Proxying the HTTP `/json/*` discovery endpoints (Puppeteer `browserURL` style). Users pass the WS URL directly.
- `webSocketDebuggerUrl` rewriting (only relevant if we proxy `/json/*`).
- Multi-tenant routing on `:9223` by token (v2).
- Metrics / dashboard.

## Implementation order

1. Refactor Go `proxyWS` to extract `relay()` (no behavior change). Verify forward mode still works.
2. Add `-tunnelURL` + tunnel-client loop in Go. Test against a hand-rolled echo target.
3. Build `core/engine/chrome_proxy.py` (registry + FastAPI WS endpoint + aiohttp `:9223` listener).
4. Wire lifespan in `app_factory.py`. Add config under `services.engine.chrome_proxy`.
5. Add session API routes (`/api/chrome-proxy/sessions`).
6. End-to-end test: real Chrome on machine A, engine on machine B, `agent-browser` on machine C.
