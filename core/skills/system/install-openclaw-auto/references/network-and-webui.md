# Network Bind and WebUI (HTTP/HTTPS)

## Bind modes

- `gateway.bind: "loopback"` -> listens on `127.0.0.1` only (recommended default)
- `gateway.bind: "lan"` -> listens on `0.0.0.0` (LAN reachable)

When bind is not loopback, configure auth token/password.

## WebUI access

- Local HTTP: `http://127.0.0.1:18789/`
- LAN HTTP: `http://<host-ip>:18789/`
- HTTPS (recommended for remote access): use Tailscale Serve or trusted reverse proxy

## Required warnings

### If using HTTP on non-localhost

Warn user:

- browser runs in non-secure context
- Control UI may require insecure-auth downgrade for token-only mode
- device identity protections can be weakened

Only use when user accepts risk.

Downgrade example (risk accepted):

```json5
{
  gateway: {
    bind: "lan",
    auth: { mode: "token", token: "REPLACE_ME" },
    controlUi: { allowInsecureAuth: true },
  },
}
```

### Preferred secure patterns

1. Keep gateway loopback-only and use SSH tunnel
2. Use Tailscale Serve with HTTPS
3. Use reverse proxy with TLS termination and controlled trusted proxies

## Quick verify

```bash
openclaw status
openclaw health
openclaw config get gateway.bind
openclaw config get gateway.auth.mode
```
