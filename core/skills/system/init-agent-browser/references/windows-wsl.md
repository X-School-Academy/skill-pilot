# Windows WSL — agent-browser Setup

## Detection

```bash
uname -r  # output contains "microsoft" or "WSL"
```

## How it works

Chrome runs on the Windows host. The `core/bin/agent-browser` CLI runs inside WSL.
A proxy binary (`chrome-devtool-proxy`) bridges CDP traffic from WSL to the Windows Chrome.

## Setup steps

1. **Copy the proxy binary to the Windows host**

   From within WSL, locate the binary:

   ```
   extensions/chrome-devtool-proxy/bin/chrome-devtool-proxy-windows-amd64.exe
   ```

   Copy it to a convenient location on the Windows host (e.g. `C:\Users\<you>\Downloads\`).

2. **Run the proxy on the Windows host**

   ```
   chrome-devtool-proxy-windows-amd64.exe
   ```

   Default behavior:
   - Listens on `0.0.0.0:9223`
   - Forwards to `ws://127.0.0.1:9222`

   The proxy will print the host IP and the full connect command:

   ```
   [proxy] listening on ws://0.0.0.0:9223
   [proxy] connect from remote: core/bin/agent-browser open URL --cdp ws://<host-ip>:9223/devtools/browser/
   ```

   The IP shown is the Windows host IP reachable from WSL.

4. **Use the cdp ws URL from inside WSL**

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
