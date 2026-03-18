#!/bin/bash
set -e

IMAGE_NAME="${IMAGE_NAME:-skillpilot/gpu-runpod:latest}"
USERNAME="${USERNAME:-ubuntu}"
USER_UID="${USER_UID:-1000}"
KEY_FILE="skillpilot-ssh-key"

# Generate SSH keypair if not already present
if [ ! -f "${KEY_FILE}" ]; then
    echo "Generating SSH keypair..."
    ssh-keygen -t ed25519 -f "${KEY_FILE}" -N "" -C "${USERNAME}@skillpilot"
    chmod 600 "${KEY_FILE}"
    echo "Private key saved to: ${KEY_FILE}"
else
    echo "Using existing SSH key: ${KEY_FILE}"
fi

docker build \
    -f Dockerfile \
    --build-arg USERNAME="${USERNAME}" \
    --build-arg USER_UID="${USER_UID}" \
    -t "${IMAGE_NAME}" .