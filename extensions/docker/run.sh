#!/bin/bash

PUBLIC_KEY="$(cat "$(dirname "$0")/skillpilot-ssh-key.pub")"
NO_DOWNLOAD_MODELS=1
COTURN_USER="${COTURN_USER:-skillpilot}"
COTURN_PASSWORD="${COTURN_PASSWORD:-skillpilot123}"

docker run -d \
  --name skill-pilot-media-mcp \
  --gpus all \
  -e PUBLIC_KEY="$PUBLIC_KEY" \
  -e COMFYUI_INSTALL_PATH="/home/ubuntu/workspace/ComfyUI" \
  ${NO_DOWNLOAD_MODELS:+-e NO_DOWNLOAD_MODELS="$NO_DOWNLOAD_MODELS"} \
  -e COTURN_USER="$COTURN_USER" \
  -e COTURN_PASSWORD="$COTURN_PASSWORD" \
  -v ~/data/models:/home/ubuntu/workspace/models \
  -p 10022:22 \
  -p 18080:8080 \
  -p 17860:7860 \
  -p 18188:8188 \
  -p 13478:3478 \
  -p 13478:3478/udp \
  -p 15349:5349 \
  -p 15349:5349/udp \
  skill-pilot/media-mcp:v_1.11
