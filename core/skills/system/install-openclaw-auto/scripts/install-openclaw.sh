#!/bin/bash
# Install OpenClaw from source

set -e

RELEASE_TAG="$1"
INSTALL_PATH="$2"

if [ -z "$RELEASE_TAG" ] || [ -z "$INSTALL_PATH" ]; then
    echo "Usage: $0 <release-tag> <install-path>"
    exit 1
fi

echo "📦 Installing OpenClaw $RELEASE_TAG to $INSTALL_PATH"

# Clone repository
echo "1/4 Cloning repository..."
git clone --depth 1 --branch "$RELEASE_TAG" https://github.com/openclaw/openclaw.git "$INSTALL_PATH"

cd "$INSTALL_PATH"

# Install dependencies
echo "2/4 Installing dependencies..."
if command -v pnpm &> /dev/null; then
    echo "Using pnpm..."
    pnpm install
elif command -v npm &> /dev/null; then
    echo "Using npm..."
    npm install
else
    echo "❌ No package manager found. Please install npm or pnpm."
    exit 1
fi

# Build UI
echo "3/4 Building UI..."
if command -v pnpm &> /dev/null; then
    pnpm ui:build
else
    npm run ui:build
fi

# Build project
echo "4/4 Building project..."
if command -v pnpm &> /dev/null; then
    pnpm build
else
    npm run build
fi

echo "✅ OpenClaw installed successfully!"
echo "Next: Configure at ~/.openclaw/openclaw.json"
