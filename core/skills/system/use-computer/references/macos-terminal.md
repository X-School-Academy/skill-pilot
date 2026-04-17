# macOS Native Terminal

Use these actions when an agent needs a visible native Terminal window while still sending shell commands through tmux.

## Open Terminal with tmux

Open a native Terminal window centered on the primary screen and attach it to a tmux session. The default requested size is 1920 x 1080 in macOS window coordinate units, which are logical points rather than guaranteed physical pixels. The requested size is clamped to the primary screen size when needed.

```json
{
  "action": "mac_open_native_terminal",
  "tmux_session_id": "agent-terminal",
  "width": 1920,
  "height": 1080
}
```

- `tmux_session_id`: Optional existing or new tmux session name. If omitted, the tool generates one.
- `width`: Optional requested window width. Defaults to 1920.
- `height`: Optional requested window height. Defaults to 1080.

The response includes:

- `window_id`: Native Terminal window id.
- `tmux_session_id`: The tmux session name to target.
- `bbox`: `[x, y, width, height]`, suitable for the `screenshot` action.
- `window_bounds`: Object form of the same bounds.

## Send Commands to tmux

Use the returned `tmux_session_id` to send commands without typing through the GUI.

```bash
tmux send-keys -t agent-terminal:0.0 "pwd" C-m
```

## Screenshot the Terminal Window

Pass the returned `bbox` to the screenshot action.

```json
{
  "action": "screenshot",
  "bbox": [415, 238, 640, 480],
  "scale": 1.0
}
```

## Close Terminal

Close a Terminal window previously opened by `mac_open_native_terminal`.

```json
{
  "action": "mac_close_native_terminal",
  "window_id": 12345
}
```

Closing the Terminal window does not necessarily kill the tmux session. Kill the tmux session separately when it is no longer needed.
