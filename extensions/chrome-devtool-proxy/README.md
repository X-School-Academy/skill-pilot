# Chrome DevTools Proxy

`chrome-devtool-proxy` proxies Chrome DevTools Protocol WebSocket traffic to a Chrome instance that exposes its DevTools endpoint, usually on `ws://127.0.0.1:9222`.

The command has two modes:

- Forward-proxy mode: listens for inbound WebSocket connections and forwards them to local Chrome.
- Tunnel-client mode: dials out to a Skill Pilot engine tunnel URL, waits for a CDP session, then connects that session to local Chrome.

## Start Chrome With CDP

Chrome must be running with remote debugging enabled before the proxy can connect to it.

```bash
google-chrome --remote-debugging-port=9222
```

On macOS, the command is usually:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

## Build

From this directory:

```bash
go build -o chrome-devtool-proxy .
```

To build the packaged Linux, macOS, and Windows binaries under `bin/`:

```bash
./build.sh
```

Existing packaged binaries are also under `bin/`.

## Forward-Proxy Mode

Forward-proxy mode is used when the machine running Chrome can accept inbound connections from the CDP client.

```bash
./chrome-devtool-proxy \
  -listenAddr=0.0.0.0:9223 \
  -targetBase=ws://127.0.0.1:9222 \
  -allowIP=*
```

Then connect a CDP client to the proxy:

```bash
agent-browser open URL --cdp ws://<proxy-host>:9223/devtools/browser/<browser-id>
```

The `/devtools/browser/<browser-id>` or `/devtools/page/<page-id>` path is forwarded to Chrome unchanged.

## Tunnel-Client Mode

Tunnel-client mode is used when the Chrome host is behind NAT or cannot accept inbound connections. In this mode the proxy dials out to the engine and parks one or more WebSocket tunnels.

```bash
./chrome-devtool-proxy \
  -tunnelURL=wss://engine.example.com/chrome-proxy?token=<token> \
  -targetBase=ws://127.0.0.1:9222 \
  -tunnelPool=1
```

When a CDP client connects through the engine, the engine sends one control frame containing the target path. The proxy then dials `targetBase + path` and relays CDP frames transparently.

Example client command:

```bash
agent-browser open URL --cdp ws://engine.example.com:9223/devtools/browser/<browser-id>
```

## Parameters

| Parameter | Default | Mode | Description |
| --- | --- | --- | --- |
| `-listenAddr` | `0.0.0.0:9223` | Forward proxy | Address the proxy listens on. Ignored when `-tunnelURL` is set. |
| `-targetBase` | `ws://127.0.0.1:9222` | Both | Upstream Chrome DevTools WebSocket base URL. The request path is appended to this value. |
| `-allowIP` | `*` | Forward proxy | Remote IP allowed to connect. Use `*` to allow any address, or set one exact client IP. Ignored when `-tunnelURL` is set. |
| `-tunnelURL` | empty | Tunnel client | Enables tunnel-client mode when set. Must be a `ws://` or `wss://` engine tunnel endpoint. |
| `-tunnelPool` | `1` | Tunnel client | Number of concurrent parked tunnels. Values below `1` are treated as `1`. |

Show command help:

```bash
./chrome-devtool-proxy -h
```

## Security Notes

- `-allowIP=*` exposes the forward proxy to any host that can reach `listenAddr`. Prefer a specific client IP when binding to a non-loopback address.
- `-tunnelURL` often contains an access token. The proxy redacts the `token` query value in logs, but shell history and process lists may still expose the original command.
- The proxy only relays WebSocket CDP traffic. It does not authenticate Chrome itself.
