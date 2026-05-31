# Feature Retrieval Index: Mac Screen Drawing and Recording

## Retrieval Keywords

screen drawing, screen recording, mac screen, mac-screen-drawing, mac-screen-recording, screen-drawing, screen-recording, screen capture, screen annotate, use-computer, mac_screen_drawing, mac_screen_recording, use_computer, computer control, desktop control

## Scope

- macOS screen drawing (annotation/overlay) tool
- macOS screen recording tool
- Computer use (desktop control) capability
- Excludes: web browser automation (see `agent-browser.md`)

## Main Behavior

- `core/bin/mac-screen-drawing` draws overlays on the macOS screen
- `core/bin/mac-screen-recording` records the macOS screen
- `core/bin/use-computer` enables AI agent computer control
- Tools wrap macOS-specific APIs for screenshot, annotation, and recording
- Supports AI-driven desktop automation

## Code Map

- `core/bin/mac-screen-drawing` — screen drawing CLI
- `core/bin/mac-screen-recording` — screen recording CLI
- `core/bin/use-computer` — computer use CLI
- `core/engine/tools/mac_screen_drawing.py` — screen drawing tool logic
- `core/engine/tools/mac_screen_recording.py` — screen recording tool logic
- `core/engine/tools/use_computer.py` — computer use tool logic
- `core/skills/system/screen-drawing/` — screen drawing skill
- `core/skills/system/screen-recording/` — screen recording skill
- `core/skills/system/use-computer/` — use computer skill

## Search Commands

```bash
find core/skills/system/screen-drawing/ -type f
find core/skills/system/screen-recording/ -type f
find core/skills/system/use-computer/ -type f
cat core/engine/tools/mac_screen_drawing.py | head -30
```

## Related Features

- `core/features/agent-browser-automation.md`
- `core/features/agent-cli.md`

## Update Notes

- macOS-specific; not available on Linux or Windows WSL
- Screen recording requires macOS screen recording permission granted to the terminal/agent process
