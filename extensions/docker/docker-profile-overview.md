# Skill Pilot Media Server

An all-in-one Docker image for Skill Pilot AI Agent **https://skill-pilot.ai** — image & video generation, talking video, text-to-speech, lip-sync, live avatar, and music creation, ready to run out of the box.

## What's Included

| Tool | Description |
|------|-------------|
| **ComfyUI** | AI image generation, video generation, and talking video via Z-Image and Wan2.2 |
| **IndexTTS** | High-quality text-to-speech synthesis |
| **MuseTalk** | Lip-sync video generation and real-time live avatar |
| **SongBloom** | AI music & song creation |

The image is built on runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04, ensuring compatibility with a wide range of NVIDIA GPUs and CUDA versions. 

Tested on NVIDIA RTX 2060 GPU (12 GB VRAM) - MuseTalk live avatar can have real-time performance at 12 FPS.

Supports local GPU acceleration with NVIDIA drivers on the host machine or Runpod Cloud environments.

## Quick Start

```bash
docker pull skillpilot/media-server:latest
docker run --gpus all \
  -p 18188:8188 -p 17860:7860 -p 18080:8080 \
  -p 13478:3478 -p 13478:3478/udp \
  -p 15349:5349 -p 15349:5349/udp \
  skillpilot/media-server:latest
```

## Exposed Ports

| Port | Protocol | Service |
|------|----------|---------|
| `22` | TCP | SSH |
| `8188` | TCP | ComfyUI |
| `7860` | TCP | Unassigned |
| `8080` | TCP | Unassigned |
| `3478` | TCP/UDP | coturn STUN/TURN (MuseTalk live avatar) |
| `5349` | TCP/UDP | coturn STUN/TURN over TLS (MuseTalk live avatar) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_KEY` | — | SSH public key to authorize for the `ubuntu` user |
| `COTURN_USER` | `skillpilot` | coturn TURN server username |
| `COTURN_PASSWORD` | `skillpilot123` | coturn TURN server password |

Set credentials at runtime for security:

```bash
docker run --gpus all \
  -e PUBLIC_KEY="your_ssh_public_key" \
  -e COTURN_USER=myuser \
  -e COTURN_PASSWORD=mysecretpassword \
  -p 18188:8188 -p 17860:7860 -p 18080:8080 \
  -p 13478:3478 -p 13478:3478/udp \
  -p 15349:5349 -p 15349:5349/udp \
  skillpilot/media-server:latest
```

When the container is running, it will automatically download the modeles by comand line below:

```bash
huggingface-cli download skill-pilot/media-mcp --local-dir /home/ubuntu/workspace/models
```

Use command below to check the downloading process in the container:

```bash
tmux attach -t download -r
```

You can use the services until the downloading process is completed. The models will be stored in the `/home/ubuntu/workspace/models` directory inside the container.

For how to use the media mcp server, please check at https://skill-pilot.ai, and find our Discord server invite link at https://skill-pilot.ai and join us for support.

## Getting Support

We offer **free community support** — no account required.

1. Visit **https://skill-pilot.ai** to find the Discord invite link.
2. Join the server and post your question in the relevant channel.
3. Include your Docker version, GPU info, and any error output for the fastest response.

## License

Free and open source https://skill-pilot.ai · **MIT License**

All codes included in this image are licensed under their respective licenses. Please refer to the individual codes for details.

---

> Built with love by the Skill Pilot team · https://skill-pilot.ai
