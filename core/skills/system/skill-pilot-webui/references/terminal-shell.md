# Direct Shell Terminal

Use the direct terminal page when the user wants a terminal-only browser view with no left nav.

## Purpose

- Demo shell usage in the browser
- Record clean terminal footage without the surrounding app shell
- Teach command-line workflows inside the Skill Pilot WebUI terminal
- Capture screenshots of a terminal session for documentation or educational video production

## Routes

### Open a direct command terminal

```text
/terminal?command=<url-encoded-command>
```

Example:

```text
/terminal?command=bash
```

This opens the standalone terminal page and runs the command through the terminal websocket flow.

### Open an existing shell tmux session directly

```text
/terminal?session=<tmux-session-name>
```

### Open an existing shell tmux session readonly

```text
/terminal?session=<tmux-session-name>&readonly=1
```

## Recommended Flow

1. Get the WebUI base URL with `core/bin/tool-cli get_webui_url` or `--dev`
2. Append the direct `/terminal?...` path
3. Open that URL with `agent-browser`
4. Wait for the xterm view to render
5. Take screenshots or record the browser as needed

## Important Distinction

- `/terminals` is the live-sessions page with navigation and session list
- `/terminal?...` is the direct terminal page without the left nav shell
