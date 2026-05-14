# Feature Retrieval Index: Media MCP Server

## Retrieval Keywords

media MCP, media server, GPU workflow, video generation, audio generation, image generation, TTS, IndexTTS, SongBloom, Wan2.2, Z-Image, MuseTalk, Whisper, Demucs, Qwen3, ComfyUI, media docker, skillpilotai/media-mcp, gpu_workflow, script_executor, playwright_utils, media tools, video workflow, audio workflow

## Scope

- MCP server for AI-driven media generation: video, audio, images, speech
- GPU workflow execution for heavy media tasks
- External script wrappers for ML models (MuseTalk, IndexTTS, SongBloom, Wan2.2, etc.)
- Excludes: camera/WebRTC (separate), live TTS real-time (see `tts-audio-service.md`), live avatar (separate)

## Main Behavior

- Media MCP server exposes tools for generating video, audio, and images via AI models
- `gpu_workflow_executor.py` runs GPU-intensive workflows
- `script_executor.py` wraps external CLI model scripts
- Supported models: IndexTTS (TTS), SongBloom (music), Wan2.2 (video), Z-Image (image), MuseTalk (avatar), Whisper (STT), Demucs (audio separation), Qwen3VL (vision), Qwen3-TTS, OmniVoice-TTS
- Deployed as a separate Docker container: `skillpilotai/media-mcp`
- Playwright utilities support browser-based media workflows

## Code Map

- `core/engine/mcp_servers/media/main.py` — Media MCP server entry point
- `core/engine/mcp_servers/media/gpu_workflow_executor.py` — GPU workflow runner
- `core/engine/mcp_servers/media/script_executor.py` — external script executor
- `core/engine/mcp_servers/media/audio_utils.py` — audio utilities
- `core/engine/mcp_servers/media/external_scripts/` — ML model CLI wrappers: `index-tts.py`, `songbloom_creator.py`, `musetalk_cli.py`, `whisper_cli.py`, `demucs_cli.py`, `qwen3vl_main.py`, `qwen3-tts-live.py`, `omnivoice-tts.py`
- `core/engine/mcp_servers/media/gpu_workflow/` — GPU workflow definitions
- `core/engine/mcp_servers/media/playwright_utils/` — Playwright helpers for browser-based media
- `core/skills/system/media/` — media skill
- `extensions/docker/` — Docker configuration for media MCP

## Search Commands

```bash
find core/engine/mcp_servers/media/ -type f
cat core/engine/mcp_servers/media/main.py | head -40
find core/engine/mcp_servers/media/external_scripts/ -type f
find core/skills/system/media/ -type f
```

## Related Features

- `core/features/tts-audio-service.md`
- `core/features/live-avatar.md`
- `core/features/image-generation.md`

## Update Notes

- Media MCP runs as a separate Docker container; see Docker Hub `skillpilotai/media-mcp` and HuggingFace `skill-pilot/media-mcp`
- GPU model weights are downloaded on first run; ensure disk space and network access
- Register media MCP in agent config after container is running
