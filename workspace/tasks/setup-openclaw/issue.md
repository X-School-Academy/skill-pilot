# OpenClaw Install Issue — OOM on t4g.small

## Status
Blocked — OpenClaw CLI commands crash with Node.js OOM on every invocation.

## Instance
- **Instance ID:** i-0fc4503a4a27bc3ce
- **Type:** t4g.small (2 GiB RAM, ARM64)
- **Region:** ap-southeast-2

## Problem
All `openclaw` CLI subcommands (`doctor`, `models auth login`, etc.) crash with:

```
FATAL ERROR: Ineffective mark-compacts near heap limit
Allocation failed - JavaScript heap out of memory
```

https://dev.to/abdielwilsn/how-to-fix-fatal-reached-heap-limit-allocation-failed-javascript-heap-out-of-memory-2ab2
export NODE_OPTIONS="--max-old-space-size=4096"



The V8 heap grows to ~923 MB before crashing. V8 auto-sizes its heap limit based on detected system RAM (~1.8 GiB), so even with a 2 GiB swap file added, the heap limit stays the same and swap doesn't help.

## What Was Completed
- OpenClaw v2026.3.13 installed successfully
- PATH fixed (`/home/ubuntu/.npm-global/bin` added to `~/.bashrc`)
- `~/.openclaw/openclaw.json` written with correct gateway token and Discord bot token
- 2 GiB swap file created and enabled (`/swapfile`)

## What Remains
- OpenAI Codex OAuth (`openclaw models auth login --provider openai-codex`)
- Systemd service setup
- Discord bot pairing

## Root Cause
`t4g.small` (2 GiB RAM) is insufficient for OpenClaw's Node.js initialization.
V8 heap auto-sizing hits the system RAM ceiling during startup.

## Recommended Fix
Upgrade to **t4g.medium** (4 GiB RAM, ~$0.0336/hr, ~$24.50/mo) or larger.
This should give V8 enough headroom to complete startup and run all CLI commands.

Summary of issue: OpenClaw's Node.js startup requires ~1 GiB heap, which exceeds the t4g.small (2 GiB RAM) budget during CLI initialization. V8 heap
auto-sizing ignores swap. Fix: re-provision with t4g.medium (4 GiB RAM) and re-run the install.
