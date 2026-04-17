# Input Actions

Use the `input` action to execute a sequence of mouse and keyboard events.

## Command

```json
{
  "action": "input",
  "actions": [
    { "type": "mouse_move", "x": 100, "y": 200, "duration": 0.5 },
    { "type": "click", "button": "left", "clicks": 1, "x": 100, "y": 200 },
    { "type": "type", "text": "Hello, world!", "interval": 0.1 },
    { "type": "key", "keys": ["enter"] },
    { "type": "hotkey", "keys": ["command", "space"] },
    { "type": "wait", "duration": 1.0 }
  ]
}
```

## Action Types

- `mouse_move`: Move the cursor to `(x, y)` over `duration` seconds.
- `click`: Click at `(x, y)` with optional `button`, `clicks`, and `interval`.
- `type`: Type the specified `text` with optional `interval` between characters.
- `key`: Press a single key or a list of keys sequentially.
- `hotkey`: Press a combination of keys simultaneously.
- `wait`: Pause execution for `duration` seconds.

## Notes

- Before using `mouse_move` or `click`, locate the target with the `find-ui-element` skill.
- Use screenshot coordinates directly unless the screenshot was scaled. If scaled, convert coordinates back to the original screen coordinate space before issuing input actions.
- Use `hotkey` for key combinations such as `["command", "v"]`.
- Use `key` for sequential presses such as `["tab", "tab", "enter"]`.
