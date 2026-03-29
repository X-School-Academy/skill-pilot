---
license: mit
tags:
  - docker
  - comfyui
  - text-to-speech
  - talking-face
  - lip-sync
  - live-avatar
  - music-generation
  - image-generation
  - video-generation
  - skill-pilot
---

# Skill Pilot Media Server

An all-in-one Media Server for Skill Pilot AI Agent https://skill-pilot.ai. Includes ComfyUI for image/video generation, IndexTTS for text-to-speech, MuseTalk for talking video and live avatar, and SongBloom for music creation.

## Included Models and Tools

| Tool | Capabilities |
|------|-------------|
| **ComfyUI** | Image generation, video generation, and talking video via Z-Image and Wan2.2 |
| **IndexTTS** | High-quality text-to-speech synthesis |
| **MuseTalk** | Lip-sync video generation and real-time live avatar |
| **SongBloom** | AI music & song creation |

## How to Use

```bash
docker pull skillpilot/media-server:latest
docker run --gpus all \
  -p 8188:8188 -p 7860:7860 -p 8080:8080 \
  -p 3478:3478 -p 3478:3478/udp \
  -p 5349:5349 -p 5349:5349/udp \
  skillpilot/media-server:latest
```

The image is built on runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04, ensuring compatibility with a wide range of NVIDIA GPUs and CUDA versions. 

Tested on NVIDIA RTX 2060 GPU (12 GB VRAM) - MuseTalk live avatar can have real-time performance at 12 FPS.

Supports local GPU acceleration with NVIDIA drivers on the host machine or Runpod Cloud environments.

Free community support — no account required.

Join our Discord server for help, setup, tips, and updates. Find the invite link at **https://skill-pilot.ai**.

## License

Free and open source https://skill-pilot.ai · **MIT License**

All models included in this repository are licensed under their respective licenses. Please refer to the individual model documentation for details.

