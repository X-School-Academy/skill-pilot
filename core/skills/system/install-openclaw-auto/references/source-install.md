# Source Install (No Onboard)

This guide installs OpenClaw from source for `macos`, `linux`, and `docker` environments.

## 1) Prerequisites

- Node.js `>=22.12.0`
- Git
- `pnpm` (preferred) or `npm`

Quick checks:

```bash
node -v
git --version
pnpm -v || npm -v
```

## 2) Choose version and clone

Use the helper script to detect latest release tag:

```bash
bash core/skills/system/install-openclaw-auto/scripts/detect-latest-release.sh
```

Install from tag:

```bash
bash core/skills/system/install-openclaw-auto/scripts/install-openclaw.sh <tag> <install-path>
```

Example:

```bash
bash core/skills/system/install-openclaw-auto/scripts/install-openclaw.sh 2026.2.10 ~/openclaw
```

After cloning, for any issue:

1. Check the cloned docs first: `<install-path>/docs/`
2. If unresolved, inspect implementation directly in `<install-path>/src/` and `<install-path>/scripts/`

## 3) Build manually (fallback)

```bash
cd <install-path>

if command -v pnpm >/dev/null 2>&1; then
  pnpm install
  pnpm ui:build
  pnpm build
else
  npm install
  npm run ui:build
  npm run build
fi
```

## 4) Platform notes

### macOS

- If Node is missing: `brew install node`
- If command not found after install, add npm global bin to `PATH`

### Linux

- Install Node 22+ first
- If `npm install -g` has permission issues, use a user prefix

### Docker container environment

Use the same source flow inside the container:

```bash
git clone --depth 1 --branch <tag> https://github.com/openclaw/openclaw.git /workspace/openclaw
cd /workspace/openclaw
pnpm install && pnpm ui:build && pnpm build
```

Persist these directories with mounts/volumes:

- `~/.openclaw/`
- `~/.openclaw/workspace/`

## 5) Run from source

From repo root:

```bash
node dist/index.js gateway
```

If CLI is globally installed, equivalent is:

```bash
openclaw gateway
```
