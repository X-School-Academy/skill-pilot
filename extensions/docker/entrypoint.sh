#!/bin/bash

# Setup SSH authorized_keys for ubuntu user
mkdir -p /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
if [ -n "$PUBLIC_KEY" ]; then
    echo "$PUBLIC_KEY" >> /home/ubuntu/.ssh/authorized_keys
    chmod 600 /home/ubuntu/.ssh/authorized_keys
fi

# Generate SSH host keys if not present and start SSH
sudo ssh-keygen -A
sudo service ssh start

# Start coturn STUN/TURN server for MuseTalk live avatar WebRTC
COTURN_USER="${COTURN_USER:-skillpilot}"
COTURN_PASSWORD="${COTURN_PASSWORD:-skillpilot123}"
sudo turnserver \
    --listening-port=3478 \
    --tls-listening-port=5349 \
    --lt-cred-mech \
    --user="${COTURN_USER}:${COTURN_PASSWORD}" \
    --realm=skill-pilot.ai \
    --log-file=/var/log/coturn.log \
    --daemon

# Download models in a tmux session (monitor with: tmux attach -t download)
tmux new-session -d -s download 'bash /home/ubuntu/workspace/download_models.sh'

# Start ComfyUI in a tmux session (monitor with: tmux attach -t comfyui)
tmux new-session -d -s comfyui 'cd /home/ubuntu/workspace/ComfyUI && .venv/bin/python main.py --listen 0.0.0.0 --force-fp16'

sleep infinity
