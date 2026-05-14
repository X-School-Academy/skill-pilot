---
name: new-agent-session
description: Start a new agent session by stopping the current agent process and launching a new prompt in the latest web or native terminal bash session.
---

# New Agent Session

Use this skill to restart or replace an agent process inside an existing tmux-backed bash session.

## When to Use This Skill

- User asks to start a new agent session with a new prompt
- User asks to start a new agent process in the current session
- User asks to replace the running agent prompt without destroying the terminal session
- You need to reuse the latest web or native terminal session created by Skill Pilot

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Run the correct CLI command and validate terminal-session targeting.
- **DevOps Engineer**: Ensure tmux session flow remains stable while agent processes are replaced.
- **Technical Writer**: Return clear status and recovery steps when no session is available.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Confirm session intent

Verify the user wants to start a new agent process in an existing terminal session, not create a brand-new terminal UI session.

### Step 2: Build the new prompt

Create one concise prompt string that clearly states the next task for the agent.
If the user asks to use a new agent skill in the new session, identify the skill name and include it clearly in the prompt with explicit instruction to use that skill.

### Step 3: Run new agent session command

From repository root, run:

```bash
core/bin/tool-cli new_agent_session "<prompt>"
```

### Step 4: Handle outcomes

- If successful, report the tmux session name returned by the command.
- If no active web/native tmux session exists, ask the user to start one from WebUI New Session first.
- If command fails, return the exact error and suggest one retry path.

## Expected Output

- Plain text confirmation that a new agent process started in the latest web/native tmux bash session.
- Clear error guidance when the command cannot target a valid session.

## Key Principles

- Always use `core/bin/tool-cli new_agent_session` for this workflow.
- Pass only prompt text to `new_agent_session`.
- Reuse the latest `webui-live-*` or `native-terminal-*` tmux session.
- Keep bash session alive; only replace the running agent process with the same CLI and options.
