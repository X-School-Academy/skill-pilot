# macOS — agent-browser Setup

## Detection

```bash
uname  # output is "Darwin"
```

## How it works

`core/bin/agent-browser --auto-connect` discovers a running Chrome instance by checking the
`DevToolsActivePort` file and common debugging ports. No proxy is needed.

## Setup steps

1. **Connect agent-browser**

   ```bash
   core/bin/agent-browser --auto-connect open https://www.google.com
   ```

   `--auto-connect` auto-discovers the running Chrome instance via CDP.

## user_preferences.md entry

```
Browser automation command: core/bin/agent-browser --auto-connect open URL
```

## Notes

- If `--auto-connect` fails, Chrome may not have remote debugging enabled.
  Open Chrome and go to `chrome://inspect/#remote-debugging` to enable it.
