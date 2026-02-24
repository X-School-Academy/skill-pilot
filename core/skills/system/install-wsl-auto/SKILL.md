---
name: install-wsl-auto
description: Installs and validates WSL on Windows with guided automation for modern and legacy installation paths. Use when a user asks to install WSL, set up Linux on Windows, or fix a broken WSL install.
---

# AI Builder - Install WSL Auto

This skill installs Windows Subsystem for Linux (WSL) safely, chooses the correct installation path, validates the environment, and gives the user a practical post-install guide.

## When to Use This Skill

- User asks to install WSL or Ubuntu on Windows.
- User needs Linux tooling on Windows for development.
- Existing WSL installation is broken and needs diagnosis or repair.
- User needs beginner-friendly setup plus verification.

## Your Roles in This Skill

- **SysOps Engineer**: Assess system readiness, run installation scripts, and apply platform-safe defaults.
- **QA Engineer**: Validate installation with deterministic checks and capture pass/fail results.
- **Customer Support**: Explain each step in plain language, confirm user decisions, and provide recovery paths.
- **Technical Writer**: Deliver a concise quick-start and troubleshooting handoff.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Key Principles

- Prefer the modern one-command flow on Windows 10 build 19041+ and Windows 11.
- Keep user-impacting actions explicit (especially restart and BIOS changes).
- Use scripts for repeatability; avoid ad-hoc command variations.
- Do not claim success until validation passes.
- If installation cannot be completed automatically, provide exact manual next steps.

## Instructions

Follow these steps in order.

### Step 1: Confirm Context and Safety

1. Confirm the user is on Windows and can run PowerShell as Administrator.
2. Explain that enabling Windows features and restarting are expected.
3. Ask whether to use the default distribution (`Ubuntu-22.04`) or a user-specified distro.
4. If the user is unsure, use:
   `references/distributions.md`
   and choose a beginner-safe default (`Ubuntu-22.04`).

### Step 2: Run Compatibility Check

1. Execute:
   `scripts/check-wsl-compatibility.ps1`
2. Parse the JSON summary at the end and decide:
   - `method = modern`: continue to Step 3A.
   - `method = manual`: continue to Step 3B.
   - `method = unsupported`: stop and provide upgrade guidance.
3. If not running as admin, stop and ask the user to reopen PowerShell as Administrator.

### Step 3A: Modern Install Path

Use this path for Windows build 19041+.

1. Execute:
   `scripts/install-wsl-modern.ps1 -Distribution <distro>`
   The script normalizes common distro aliases and rejects unsupported distro names.
2. If the script reports `needsRestart = true`, guide the restart.
3. After restart, continue with Step 4 and Step 5.

### Step 3B: Manual Install Path

Use this path for older Windows 10 builds.

1. Pre-restart phase:
   `scripts/install-wsl-manual.ps1 -Distribution <distro>`
2. Restart Windows when prompted.
3. Post-restart phase:
   `scripts/install-wsl-manual.ps1 -ContinueAfterRestart -Distribution <distro>`
   The script normalizes common distro aliases and validates availability.
4. If kernel update is required, follow the official Microsoft package flow noted by the script output.
5. Continue with Step 4 and Step 5.

### Step 4: First-Run User Setup

1. Ensure the Linux distro launches once.
2. Guide user to create Linux username and password.
3. Explain password entry has no visible characters in terminal.
4. Confirm the user can reopen WSL after first-run setup.

### Step 5: Validate Installation

1. Execute:
   `scripts/test-wsl.ps1 -Strict`
2. Confirm:
   - WSL command available
   - At least one distro installed
   - At least one distro is running WSL 2
   - Command execution inside WSL works
   - Basic Linux toolchain works (`apt` available)
   - Network check inside WSL works
   - `/mnt/c` access works
3. If strict mode fails only on network checks in constrained environments, rerun:
   `scripts/test-wsl.ps1`
   and treat network as advisory.
4. If checks fail, route to `references/troubleshooting.md`.

### Step 6: Handoff and Next Steps

1. Provide a short result summary: install method, distro, and validation outcome.
2. Provide quick-start guidance from:
   `references/user-guide.md`
3. If unresolved issues remain, provide targeted fixes from:
   `references/troubleshooting.md`
4. If distro selection needs adjustment or reinstall, use:
   `references/distributions.md`
5. End with concrete next action for the user.

## Expected Output

Provide a structured final report with:

- Environment summary (Windows build, chosen path)
- Actions executed (scripts and parameters)
- Validation results (pass/fail per test)
- Any remaining blockers with exact remediation steps
- Quick-start commands for daily use (`wsl`, `wsl --shutdown`, `sudo apt update`)

## Common Issues

- Installation requires restart before WSL commands are available.
- BIOS virtualization disabled blocks WSL 2.
- Corporate policy can block Windows optional feature changes.
- DNS or VPN conflicts can break WSL networking after install.

When these occur, use `references/troubleshooting.md` and report exactly which step failed.
