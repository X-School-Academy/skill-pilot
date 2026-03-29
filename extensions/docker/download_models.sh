#!/bin/bash
set -e

if [ -n "$NO_DOWNLOAD_MODELS" ]; then
    echo "=== NO_DOWNLOAD_MODELS is set, skipping model downloads ==="
    exit 0
fi

(
echo "=== Downloading skill-pilot/media-mcp models ==="
mkdir -p /home/ubuntu/workspace/models
/home/ubuntu/.local/bin/uv run huggingface-cli download skill-pilot/media-mcp \
    --local-dir /home/ubuntu/workspace/models
)

echo "=== All models downloaded successfully ==="

