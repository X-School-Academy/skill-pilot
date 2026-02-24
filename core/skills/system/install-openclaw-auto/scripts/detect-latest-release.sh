#!/bin/bash
# Auto-detect latest OpenClaw release from GitHub

set -e

echo "🔍 Detecting latest OpenClaw release..."

# Fetch latest release info from GitHub API
LATEST_RELEASE=$(curl -s https://api.github.com/repos/openclaw/openclaw/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_RELEASE" ]; then
    echo "❌ Failed to detect latest release"
    echo "Falling back to main branch"
    LATEST_RELEASE="main"
else
    echo "✅ Latest release: $LATEST_RELEASE"
fi

# Output for capture
echo "$LATEST_RELEASE"
