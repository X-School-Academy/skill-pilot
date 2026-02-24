---
name: screen-recording
description: Record the macOS main monitor from CLI only using tmux, ffmpeg, and sox. Use this skill when you need background start/stop recording control without MCP.
---

# AI Builder - Screen Recording

This skill controls a macOS-only screen recorder via CLI. It records the **main monitor** using `ffmpeg` and captures audio using `sox`, both running in `tmux` sessions.

## When to Use This Skill

- You need to start screen recording and keep it running in the background.
- You need to stop recording later and produce a final mp4 file.
- You need a CLI-only flow (not MCP) for screen recording.

## Your Roles in This Skill

- **QA Engineer**: Verify recording start/stop behavior and output file correctness.
- **DevOps Engineer**: Manage background tmux lifecycle and dependency checks.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Verify Environment

- macOS only.
- `ffmpeg`, `sox`, and `tmux` must be available in `PATH`.
- Run commands from project root.

### Step 2: Start Recording

```bash
core/bin/mac-screen-recording start
```

Optional arguments:

```bash
core/bin/mac-screen-recording start --fps 30 --output .skillpilot/temp/screen-recording/my-session.mp4
```

If ffmpeg device auto-detection fails on your machine, pass the screen device index explicitly:

```bash
core/bin/mac-screen-recording start --screen-device-index 1
```

### Step 3: Check Status

```bash
core/bin/mac-screen-recording status
```

### Step 4: Stop Recording

```bash
core/bin/mac-screen-recording stop
```

This stops tmux sessions, finalizes media, and writes the final mp4 path in output JSON.

## Expected Output

- `start`: JSON with `run_id`, output path, and tmux session names.
- `status`: JSON showing whether recording is active and tmux sessions are alive.
- `stop`: JSON with `final_file` path.

## Key Principles

- Keep one active recording at a time per state file.
- Always use `stop` to finalize output cleanly.
- Use default state path `.skillpilot/temp/screen-recording/state.json` unless a different workflow is required.
