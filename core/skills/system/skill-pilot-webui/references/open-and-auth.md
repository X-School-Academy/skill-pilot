# Open And Authenticate

Use the live local WebUI URL instead of hardcoding ports.

## Get the URL

- Production or runtime-default mode:

```bash
core/bin/tool-cli get_webui_url
```

- Development mode:

```bash
core/bin/tool-cli get_webui_url --dev
```

The command returns a browser-ready HTTP URL including the current auth token query parameter when the engine has one loaded.

If the command reports that the Skill Pilot engine is not started, start it first:

```bash
./skillpilot.sh start
```

For development mode:

```bash
./skillpilot.sh start --dev
```

Example:

```text
http://127.0.0.1:3003?token=...
```

## Open with Browser Automation

Use the `agent-browser` skill and open the exact returned URL.

Typical sequence:

```bash
core/bin/agent-browser open "$(core/bin/tool-cli get_webui_url)"
core/bin/agent-browser wait --load networkidle
core/bin/agent-browser snapshot -i
```

For development mode:

```bash
core/bin/agent-browser open "$(core/bin/tool-cli get_webui_url --dev)"
core/bin/agent-browser wait --load networkidle
core/bin/agent-browser snapshot -i
```

## Verification

- Confirm the page title and visible Skill Pilot shell
- Re-snapshot after navigation or major state changes
- If the page is already open in the agent browser, refresh or navigate directly to the requested route

## Notes

- This is a trusted local app flow
- Do not read `config/.env` directly for the token
- Use the URL returned by the CLI as the source of truth
