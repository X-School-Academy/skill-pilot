# macOS Init

## Detection

```bash
uname
```

The output is `Darwin`.

## How It Works

`core/bin/agent-browser --auto-connect` discovers a running Chrome instance by checking the `DevToolsActivePort` file and common debugging ports. No proxy is needed.

## Setup Steps

Connect agent-browser:

```bash
core/bin/agent-browser --auto-connect open https://www.google.com
```

`--auto-connect` auto-discovers the running Chrome instance via CDP.

## User Preference Entry

```text
Browser automation command: core/bin/agent-browser --auto-connect open URL
```

## Notes

If `--auto-connect` fails, Chrome may not have remote debugging enabled. Open Chrome and go to `chrome://inspect/#remote-debugging` to enable it.
