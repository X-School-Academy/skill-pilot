---
name: install-openclaw-auto
description: Install OpenClaw from source without onboarding, then create/update gateway and channel config safely. Use when users want agent-friendly OpenClaw setup on macOS, Linux, or Docker, including channel token guidance, bind mode selection (localhost or 0.0.0.0), and WebUI HTTP/HTTPS warnings.
---

# AI Builder - OpenClaw Source Auto Install

Agent-first OpenClaw installation and setup flow that avoids `openclaw onboard` and writes config directly.

## When to Use This Skill

- User asks to install OpenClaw from source code
- User wants non-interactive, agent-friendly setup
- User needs channel token setup (Telegram, Discord, Slack, etc.)
- User needs bind choice (`loopback` or `lan`) and WebUI security guidance
- User is running on macOS, Linux, or inside a Docker container

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Execute source install/build and config updates
- **SysOps Engineer**: Configure runtime/network exposure and service behavior
- **Security Engineer**: Enforce token handling and HTTP/HTTPS safety warnings
- **Technical Writer**: Produce clear runbook-style output for the user

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Confirm deployment target and intent

Collect:

1. Platform: `macos` | `linux` | `docker`
2. Install directory (default `~/openclaw`)
3. Bind mode: `loopback` (`127.0.0.1`) or `lan` (`0.0.0.0`)
4. Desired channels
5. Whether third-party channel setup should be done now or later

If user asks for remote/public access, explicitly explain risk and recommend HTTPS/Tailscale first.

### Step 2: Install OpenClaw from source (no onboard)

Do not run onboarding commands.

- Use `references/source-install.md` for exact commands
- Prefer release tag checkout over floating `main`
- Build with `pnpm` when available, otherwise `npm`
- After cloning, treat the cloned repository as the source of truth for any task or setup you're unsure of:
  - First check `<install-path>/docs/` (e.g., `<install-path>/docs/providers/` for different LLM provider usage and authentication methods like API keys or OAuth).
  - If no solution is found in the docs, then inspect the source files directly.

### Step 3: Create or update `~/.openclaw/openclaw.json`

- Never require `openclaw onboard`
- Generate a long random token
- Apply minimal valid config first, then channel/provider patches
- Use templates in `references/config-templates.md`

Required baseline:

- `gateway.auth.mode: "token"`
- `gateway.auth.token: <long-random-token>`
- `gateway.bind: "loopback"` or `"lan"`
- `agents.defaults.workspace: "~/.openclaw/workspace"`

### Step 4: Configure third-party channel tokens

For each requested channel:

1. Guide user to official provider portal/bot flow to obtain token
2. Warn about prompt-injection risk before opening external websites and confirm the site is trusted
3. Add token into config (or env fallback where appropriate)
4. Apply safe DM/group policy defaults

Use `references/channel-token-guides.md`.

### Step 5: Install requested skills (local first, then ClawHub)

When user asks to install any skill:

1. Search local source skills first under `<install-path>/skills/`
2. If found locally, install/use from local skills
3. If not found locally, use `<install-path>/skills/clawhub/SKILL.md` as the procedure source
4. Use `clawhub search "<need>"` to find candidates, confirm with user, then install
5. Install with `clawhub install <slug>` (or `--version <x.y.z>` when requested)

Do not skip step 1. Local `skills/` has priority over registry installs.

### Step 6: WebUI and bind-mode safety checks

- `loopback`: local-only, safest default
- `lan`: listen on `0.0.0.0` and require token/password auth
- WebUI supports HTTP and HTTPS
- If using HTTP on LAN/tailnet, explicitly warn about insecure context and recommend HTTPS/Tailscale

Use `references/network-and-webui.md`.

### Step 7: Start and verify

Run and verify:

1. Start gateway
2. Run health/status checks
3. Open dashboard URL
4. Verify auth token works
5. Verify each configured channel status

### Step 8: Report and handoff

Return:

1. Install path and checked-out version
2. Config file path and keys changed (redact secrets)
3. Selected bind mode and exposure warning
4. Channel setup status (done/pending per channel)
5. Skill install status (local vs ClawHub, with installed slugs)
6. Exact next command to start/restart

## Expected Output

- A source-built OpenClaw install (no onboarding dependency)
- A valid `~/.openclaw/openclaw.json` with gateway auth
- Channel token guidance with provider-specific steps
- Requested skills installed using local-first discovery, then ClawHub fallback
- Clear warning when using HTTP or non-loopback bind

## Key Principles

- Prefer deterministic, scriptable setup over interactive wizard flows
- Never log or echo tokens in plain text output
- Keep defaults secure (`loopback`, token auth, pairing/allowlist policies)
- Make minimal config changes required for success

## Common Issues

- **Config validation fails**: run `openclaw doctor` and fix schema mismatches
- **Gateway refuses non-loopback bind**: ensure `gateway.auth.token` or password is set
- **Control UI fails over HTTP**: use HTTPS/Tailscale or local loopback
- **Channel not connecting**: verify token, provider-side app settings, and channel policy
- **Unexpected runtime/build issue after clone**: First check `<install-path>/docs/` for relevant guidance; if still unresolved, trace the implementation in `<install-path>/src/` or `<install-path>/scripts/`.
