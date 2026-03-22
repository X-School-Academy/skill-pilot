#!/usr/bin/env bash
set -euo pipefail

# Defaults
LISTEN_ADDR="0.0.0.0:9223"
TARGET_BASE="ws://127.0.0.1:9222"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build chrome-devtool-proxy binaries for Linux, macOS (amd64+arm64), and Windows.
Outputs are placed in the bin/ directory.

Options:
  --listenAddr <addr>   Address the proxy listens on (default: "$LISTEN_ADDR")
  --targetBase <url>    Upstream WebSocket target base URL (default: "$TARGET_BASE")
  --help                Show this help message and exit

Examples:
  $(basename "$0")
  $(basename "$0") --listenAddr 0.0.0.0:9224 --targetBase ws://127.0.0.1:9222
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --listenAddr)
            LISTEN_ADDR="$2"; shift 2 ;;
        --targetBase)
            TARGET_BASE="$2"; shift 2 ;;
        --help|-h)
            usage ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Run '$(basename "$0") --help' for usage." >&2
            exit 1 ;;
    esac
done

LDFLAGS="-s -w \
  -X 'main.listenAddr=${LISTEN_ADDR}' \
  -X 'main.targetBase=${TARGET_BASE}'"

mkdir -p bin

echo "Building with defaults: listenAddr=${LISTEN_ADDR}  targetBase=${TARGET_BASE}"
echo ""

build() {
    local goos=$1 goarch=$2 out=$3
    echo "  -> bin/${out}"
    GOOS="$goos" GOARCH="$goarch" go build -ldflags="${LDFLAGS}" -o "bin/${out}" .
}

build linux   amd64 chrome-devtool-proxy-linux-amd64
build darwin  arm64 chrome-devtool-proxy-darwin-arm64
build windows amd64 chrome-devtool-proxy-windows-amd64.exe

echo ""
echo "Done. Binaries in bin/:"
ls -lh bin/
