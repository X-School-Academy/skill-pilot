# Linux GUI Init

## Detection

Check for a display server:

```bash
echo $DISPLAY
echo $WAYLAND_DISPLAY
```

If either variable is set, a GUI display is available.

## How It Works

`core/bin/agent-browser --auto-connect` discovers a running Chrome instance by checking common debugging ports. No proxy is needed when a display is available.

## Setup Steps

Connect agent-browser:

```bash
core/bin/agent-browser --auto-connect open https://www.google.com
```

## User Preference Entry

```text
Browser automation command: core/bin/agent-browser --auto-connect open URL
```

## Notes

If `--auto-connect` fails, Chrome may not have remote debugging enabled. Open Chrome and go to `chrome://inspect/#remote-debugging` to enable it.
