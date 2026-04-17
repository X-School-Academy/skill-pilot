---
name: use-computer
description: Control the computer by taking screenshots, moving the mouse, clicking, and typing. Use this skill when you need to interact with GUI applications or perform actions that require visual feedback.
---

# Use Computer

This skill enables an agent to interact with the computer's graphical user interface (GUI). It can retrieve screen information, take screenshots of specific regions, and perform mouse and keyboard actions.

## When to Use This Skill

- User needs to interact with GUI applications programmatically
- User asks to automate mouse and keyboard actions
- User wants to take screenshots of specific screen regions
- User needs to test UI flows or perform visual verification
- User requires automated interaction with desktop applications

## Your Roles in This Skill

- **QA Engineer**: Use computer control to perform automated UI testing and verification. Take screenshots to capture UI states and verify visual elements. Execute test scripts that require GUI interaction. Verify application behavior through visual feedback.
- **DevOps Engineer**: Execute Python scripts for computer control operations. Manage system permissions for screen recording and accessibility. Configure screen coordinates and interaction parameters. Troubleshoot PyAutoGUI fail-safe and permission issues.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.
## Instructions

All interactions are performed via the `core/bin/use-computer` CLI from the project root:

```bash
core/bin/use-computer --json_str '<JSON_COMMAND>'
```

The script returns a JSON response wrapped in `<output></output>` tags.

### 1. Get Screen Information
Use this to understand the monitor setup and primary screen resolution.

**Command:**
```json
{"action": "screen_info"}
```

### 2. Take a Screenshot
For screenshot payloads, return fields, scaling, pointer markers, and coordinate correction, refer to `references/screenshot.md`.

### 3. Find Coordinates for Actions (Required)
Before any `mouse_move` or `click`, use agent skill `find-ui-element` to locate the target UI element and derive coordinates.

Recommended flow:
- Take a screenshot with `draw_pointer: true`.
- Use `find-ui-element` on that screenshot to get the element bounding box.
- Convert the bounding box to action coordinates (usually the center point).
- Use those coordinates in `input` actions.

### 4. Perform Actions
For mouse, keyboard, hotkey, typing, and wait action payloads, refer to `references/input-actions.md`.

### 5. macOS Native Terminal
If the task needs a visible macOS Terminal window backed by tmux, refer to `references/macos-terminal.md`.

## Usage Notes

- **Coordinates**: (0, 0) is the top-left corner of the primary monitor.
- **Fail-safe**: PyAutoGUI has a fail-safe feature. Moving the mouse to any corner of the screen will abort the script.
- **Scaling**: Use a lower `scale` (e.g., 0.5 or 0.25) when taking screenshots for large screens to reduce processing time and token usage if sending to an LLM.
- **Permissions**: Ensure the terminal/IDE has "Screen Recording" and "Accessibility" permissions in System Settings (macOS).
