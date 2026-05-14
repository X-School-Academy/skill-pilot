# Windows WSL Init

## Detection

```bash
uname -r
```

The output contains `microsoft` or `WSL`.

## How It Works

Chrome runs on the Windows host. The `core/bin/agent-browser` CLI runs inside WSL. A proxy binary, `chrome-devtool-proxy`, bridges CDP traffic from WSL to Windows Chrome.

## Setup Steps

1. Copy the proxy binary to the Windows host:

```text
extensions/chrome-devtool-proxy/bin/chrome-devtool-proxy-windows-amd64.exe
```

Copy it to a convenient Windows location, such as `C:\Users\<you>\Downloads\`.

2. Run the proxy on the Windows host:

```text
chrome-devtool-proxy-windows-amd64.exe
```

Default behavior:

- Listens on `0.0.0.0:9223`.
- Forwards to `ws://127.0.0.1:9222`.

The proxy prints the host IP and full connect command:

```text
[proxy] listening on ws://0.0.0.0:9223
[proxy] connect from remote: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

3. Use the CDP WebSocket URL from inside WSL:

```bash
core/bin/agent-browser open https://www.google.com --cdp ws://<host-ip>:9223/devtools/browser/
```

## Proxy Options

```text
-allowIP string      Remote IP allowed to connect; '*' permits any address (default "*")
-listenAddr string   Address to listen on (default "0.0.0.0:9223")
-targetBase string   Upstream WebSocket target base URL (default "ws://127.0.0.1:9222")
```

## User Preference Entry

```text
Browser automation command: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```
