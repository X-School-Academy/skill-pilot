---
name: dev-swarm-headless-ai-agents
description: Run popular AI code agents (Claude Code, Codex, Gemini CLI) in headless or non-interactive mode for automation, scripting, and programmatic execution. Use when automating AI agent tasks or integrating into CI/CD pipelines.
---

# AI Builder - Headless AI Agents

This skill provides instructions for running popular AI code agents in headless (non-interactive) mode, enabling automation, scripting, and programmatic execution without user interaction.

## When to Use This Skill

- Running AI code agents in automated pipelines or scripts
- Integrating AI agents into CI/CD workflows
- Executing batch tasks with AI agents programmatically
- Building web services or APIs that invoke AI agents
- Running AI agents without terminal interaction

## Your Roles in This Skill

- **DevOps Engineer**: Configure and execute headless agent commands, set up automation pipelines, and handle environment configuration.
- **Backend Developer**: Integrate headless agents into applications, scripts, or services.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps to run an AI code agent in headless mode:

### Step 1: Identify the AI Code Agent

Determine which AI code agent to run in headless mode. Route to the appropriate reference file:

- If using **Claude Code**, refer to `references/claude-code.md`
- If using **Codex**, refer to `references/codex.md`
- If using **Gemini CLI**, refer to `references/gemini-cli.md`
- If using **other AI code agents**, run `<agent-name> --help` to discover available flags for non-interactive/headless mode. Look for flags like `--print`, `--non-interactive`, `--batch`, `--yes`, `--auto-approve`, or similar

### Step 2: Verify Installation

As a DevOps Engineer, verify the agent is installed:

```bash
# Claude Code
claude --version

# Codex
codex --version

# Gemini CLI
gemini --version
```

If not installed, use the `dev-swarm-install-ai-code-agent` skill.

### Step 3: Choose Execution Mode

Each agent supports different headless modes:

| Agent | Mode | Use Case |
|-------|------|----------|
| Claude Code | `--print` | Print output and exit (piping) |
| Codex | `exec` | Non-interactive execution |
| Gemini CLI | Positional prompt | One-shot execution |

### Step 4: Configure Permissions

**Important:** Headless mode typically requires bypassing permission prompts.

| Agent | Permission Flag | Security Note |
|-------|-----------------|---------------|
| Claude Code | `--dangerously-skip-permissions` | Bypasses all prompts |
| Codex | `--ask-for-approval never` | Auto-approve all actions |
| Gemini CLI | `--yolo` | Auto-accept all actions |

**Security Warning:** Only use these flags in trusted, sandboxed environments.

### Step 5: Execute the Agent

Refer to the agent-specific reference file for detailed command syntax and examples.

**Quick Reference (Minimal Commands):**

```bash
# Claude Code (headless)
claude --print --dangerously-skip-permissions "your prompt here"

# Codex (headless)
codex --ask-for-approval never --sandbox workspace-write exec "your prompt here"

# Gemini CLI (headless)
gemini --yolo --sandbox "your prompt here"
```

### Step 6: Handle Output

Configure output format based on your needs:

- **Text output**: Default for all agents
- **JSON output**: Available for structured processing
- **Streaming output**: For real-time processing

See agent-specific reference files for output format options.

## Key Principles

- **Security first**: Only use permission-bypass flags in sandboxed/trusted environments
- **Sandbox when possible**: Use sandbox modes to limit agent capabilities
- **Structured output**: Use JSON output for programmatic processing
- **Timeout handling**: Set appropriate timeouts for long-running tasks
- **Error handling**: Check exit codes and stderr for failures

## Common Issues

**Issue: Agent hangs waiting for input**
- Solution: Ensure all permission-bypass flags are set correctly

**Issue: Command not found**
- Solution: Verify agent is installed and in PATH

**Issue: Permission denied errors**
- Solution: Check working directory permissions and sandbox settings

**Issue: Output parsing fails**
- Solution: Use JSON output format (`--output-format json`) for reliable parsing
