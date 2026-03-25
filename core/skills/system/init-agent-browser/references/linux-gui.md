# Linux with GUI — agent-browser Setup

## Detection

```bash
# Check for a display server
echo $DISPLAY          # X11 (e.g. :0)
echo $WAYLAND_DISPLAY  # Wayland (e.g. wayland-0)
```

If either variable is set, a GUI display is available.

## How it works

`core/bin/agent-browser --auto-connect` discovers a running Chrome instance by checking common
debugging ports. No proxy is needed when a display is available.

## Setup steps

1. **Connect agent-browser**

   ```bash
   core/bin/agent-browser --auto-connect open https://www.google.com
   ```

## user_preferences.md entry

```
Browser automation command: core/bin/agent-browser --auto-connect open URL
```

## Notes

- If `--auto-connect` fails, Chrome may not have remote debugging enabled.
  Open Chrome and go to `chrome://inspect/#remote-debugging` to enable it.
