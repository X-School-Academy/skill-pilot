# Docker / Linux without GUI — agent-browser Setup

## Detection

No display environment variable is set:

```bash
echo $DISPLAY          # empty
echo $WAYLAND_DISPLAY  # empty
```

## How it works

Chrome runs on the host machine (with a GUI). The `core/bin/agent-browser` CLI runs inside the
container or headless Linux environment. A proxy binary (`chrome-devtool-proxy`) bridges
CDP traffic from the container to the host Chrome.

## Available proxy binaries

Located under `extensions/chrome-devtool-proxy/bin/`:

| Platform         | Binary                                    |
| ---------------- | ----------------------------------------- |
| Linux amd64      | `chrome-devtool-proxy-linux-amd64`        |
| Linux arm64      | `chrome-devtool-proxy-linux-arm64`        |
| macOS arm64      | `chrome-devtool-proxy-darwin-arm64`       |
| macOS amd64      | `chrome-devtool-proxy-darwin-amd64`       |
| Windows amd64    | `chrome-devtool-proxy-windows-amd64.exe`  |

## Setup steps

1. **Copy the correct proxy binary to the host machine**

   Identify the host OS and architecture, then copy the matching binary.

2. **Run the proxy on the host**

   Make it executable and run it:

   ```bash
   chmod +x chrome-devtool-proxy-<platform>
   ./chrome-devtool-proxy-<platform>
   ```

   Default behavior:
   - Listens on `0.0.0.0:9223`
   - Forwards to the local Chrome CDP endpoint

   The proxy will print the host IP and the full connect command:

   ```
   [proxy] listening on ws://0.0.0.0:9223
   [proxy] connect from remote: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
   ```

3. **Use the cdp ws URL from inside the container**

   Copy the `ws://` URL printed by the proxy and pass it to agent-browser:

   ```bash
   core/bin/agent-browser open https://www.google.com --cdp ws://<host-ip>:9223
   ```

## Proxy options

```
-allowIP string      Remote IP allowed to connect; '*' permits any address (default "*")
-listenAddr string   Address to listen on (default "0.0.0.0:9223")
-targetBase string   Upstream WebSocket target base URL (default "ws://127.0.0.1:9222")
```

## user_preferences.md entry

```
Browser automation command: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
```

## Notes

- If the container cannot reach the host IP, check Docker network settings and firewall rules
- The `--allowIP` flag can restrict which IPs are permitted to connect to the proxy
