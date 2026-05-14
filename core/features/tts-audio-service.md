# Feature Retrieval Index: TTS and Audio Service

## Retrieval Keywords

TTS, text-to-speech, audio, live TTS, tts_service, live_tts, live-tts-text-to-audio, audio chat, rest/audio, audio API, speech synthesis, qwen3-tts, omnivoice-tts, IndexTTS, sound

## Scope

- Real-time text-to-speech via the engine TTS service
- Live TTS MCP server for AI agent audio output
- Audio chat endpoint
- Excludes: heavy GPU TTS via media MCP (see `media-mcp-server.md`), Discord audio (separate)

## Main Behavior

- `POST /rest/audio` handles audio/TTS-based chat input and output
- `tts_service.py` provides the TTS service layer
- Live TTS MCP server exposes real-time speech synthesis to AI agents
- Supports streaming audio output

## Code Map

- `core/engine/tts_service.py` — TTS service logic
- `core/engine/routes_integrations.py` — `POST /rest/audio` handler
- `core/engine/mcp_servers/live_tts/main.py` — Live TTS MCP server entry point
- `core/skills/system/live-tts-text-to-audio/` — live TTS skill

## Search Commands

```bash
cat core/engine/tts_service.py | head -40
rg "rest/audio" core/engine/routes_integrations.py -n
cat core/engine/mcp_servers/live_tts/main.py | head -40
find core/skills/system/live-tts-text-to-audio/ -type f
```

## Related Features

- `core/features/media-mcp-server.md`
- `core/features/llm-ai-chat.md`
- `core/features/live-avatar.md`

## Update Notes

- Live TTS MCP server must be registered separately in agent config
- TTS provider configuration (voice, model) in `settings.json5` under `services.tts`
