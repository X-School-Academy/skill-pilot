---
name: screen-drawing
description: Draw temporary bounding-box overlays on macOS in quick mode or manual mode. Use when you need to highlight screen regions, and run manual drawing in a tmux background session with explicit start/stop control.
---

# AI Builder - Screen Drawing

This skill provides a macOS screen overlay tool for drawing bounding boxes.

- `quick` mode: draw one rectangle and exit automatically (default 5 seconds).
- `manual` mode: run a long-lived process for user-driven rectangle drawing, typically in tmux.

## When to Use This Skill

- You need to visually highlight a target region with a temporary rectangle.
- You need a short-lived bounding box overlay that auto-exits after 5 seconds.
- You need a user-controlled manual drawing session that can run in the background.
- You need explicit start/stop lifecycle control for drawing sessions.

## Your Roles in This Skill

- **QA Engineer**: Validate rectangle position and duration against the requested target area.
- **DevOps Engineer**: Start, monitor, and stop manual drawing processes safely using tmux.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Confirm Environment

- This skill is macOS-only.
- Run commands from the project root.
- Ensure the terminal app has required macOS permissions if overlays do not appear.

### Step 2: Quick Rectangle (Auto Exit in 5s)

Draw a single bounding box and exit after 5 seconds:

```bash
core/bin/mac-screen-drawing --mode quick --bbox '200,180,640,360' --duration 5
```

Notes:
- `bbox` format is `x,y,width,height` in top-left screen coordinates.
- If `--bbox` is omitted, the tool draws a centered default rectangle.
- `--duration` defaults to `5`.

### Step 3: Start Manual Drawing in tmux (Background)

Start a background manual drawing process:

```bash
tmux new-session -d -s screen-drawing 'core/bin/mac-screen-drawing --mode manual --state-path .skillpilot/temp/screen-drawing-state.json'
```

Check session status:

```bash
tmux has-session -t screen-drawing && echo running
```

In manual mode:
- Drag with mouse to draw rectangles.
- The latest rectangle is saved to `--state-path`.

### Step 4: Stop Manual Drawing on Request

Stop the background manual drawing session:

```bash
tmux kill-session -t screen-drawing
```

### Step 5: Optional State Inspection

Read the latest manual rectangle coordinates:

```bash
cat .skillpilot/temp/screen-drawing-state.json
```

## Expected Output

- Quick mode: temporary rectangle overlay shown for configured duration, then process exits.
- Manual mode: persistent drawing process until stopped, with latest rectangle written to state JSON.

## Key Principles

- Use `quick` mode for one-off guidance overlays.
- Use `manual` mode only when long-running interaction is required.
- Always stop tmux sessions when user requests completion.
