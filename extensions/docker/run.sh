#!/bin/bash

PUBLIC_KEY="$(cat "$(dirname "$0")/skillpilot-ssh-key.pub")"
NO_DOWNLOAD_MODELS=1

docker run -d \
  --name skill-pilot-media-mcp \
  --gpus all \
  -e PUBLIC_KEY="$PUBLIC_KEY" \
  -e COMFYUI_INSTALL_PATH="/home/ubuntu/workspace/ComfyUI" \
  ${NO_DOWNLOAD_MODELS:+-e NO_DOWNLOAD_MODELS="$NO_DOWNLOAD_MODELS"} \
  -v ~/data/models:/home/ubuntu/workspace/models \
  -p 10022:22 \
  -p 18080:8080 \
  -p 17860:7860 \
  -p 18188:8188 \
  skill-pilot/media-mcp:latest
