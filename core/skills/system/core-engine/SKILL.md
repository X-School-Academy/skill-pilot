---
name: core-engine
description: Manage core engine lifecycle via core/bin/tool-cli commands for engine-restart and engine-reload. Use when the user asks to restart engine from memory or reload .env updates and restart safely.
---

# AI Builder - Core Engine

Control core engine restart/reload through socket-driven commands.

## When to Use This Skill

- User asks to restart core engine
- User asks to reload updated `config/.env` and apply changes
- User asks to control engine lifecycle from CLI without manual tmux interaction

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Execute engine control commands safely
- **SysOps Engineer**: Validate lifecycle intent and runtime impact
- **Technical Writer**: Report action, signal path, and expected result

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Choose operation

Map user intent:

1. `engine-restart`: restart engine process from in-memory environment only to reload config json/json5 files if user has updated these file manually
2. `engine-reload`: read latest `.env` and config into memory, then restart engine process if user has updated `.env` manually 

### Step 2: Execute command

From repo root:

```bash
core/bin/tool-cli engine-restart
```

```bash
core/bin/tool-cli engine-reload
```

### Step 3: Report expected behavior

- `engine-restart`: does not re-read `.env`
- `engine-reload`: re-reads `.env` first, then restarts
- Works for dev-server (`--reload`) and direct `main.py` execution

### Step 4: Confirm result

Return command output and note that active sessions may reconnect during restart.

## Expected Output

- A successful engine restart/reload request acknowledged by tool-cli
- Clear summary of whether `.env` was re-read

## Key Principles

- Use signal-based control via engine socket, not manual process killing
- Keep restart and reload semantics explicit
- Prefer `engine-reload` after key changes in `config/.env` manually
