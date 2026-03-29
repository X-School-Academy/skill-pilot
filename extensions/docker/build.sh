#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="skillpilotai/media-mcp:v_1.11"
CONTAINER_NAME="skill-pilot-media-mcp"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME"
fi

docker build --no-cache -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile_v_1.11" "$SCRIPT_DIR"
