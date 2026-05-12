# Feature Retrieval Index: LLM Providers and AI Chat

## Retrieval Keywords

LLM, AI chat, LLM providers, chat API, rest/chat, llm_service, llm.py, default provider, stop LLM, audio chat, TTS chat, code executor chat, AI providers, ai_providers.json5, OpenAI, Anthropic, Claude, ollama, openai-compatible, claude-compatible, llm adapter, local inference, local-openai-infer

## Scope

- LLM provider listing and runtime stop
- REST chat endpoint for AI conversations
- Audio/TTS chat integration
- AI provider configuration (`ai_providers.json5`)
- Excludes: config/settings for provider defaults (see `config-settings-mcp-skills.md`)

## Main Behavior

- `GET /api/llm/providers` lists configured AI providers
- `POST /api/llm/stop` stops an in-progress LLM generation
- `POST /rest/chat` is the main chat endpoint; supports streaming
- `POST /rest/audio` handles audio/TTS-based chat
- `POST /rest/code_v1` executes code with AI context
- LLM service reads from `config/ai_providers.json5` for provider configuration
- Local inference supported via `core/bin/local-openai-infer`

## Code Map

- `core/engine/llm.py` — core LLM interaction logic
- `core/engine/llm_service.py` — LLM service layer
- `core/engine/routes_integrations.py` — `/api/llm/*`, `/rest/chat`, `/rest/audio`, `/rest/code_v1`
- `core/engine/workflow/llm_adapter.py` — LLM adapter for workflow execution
- `core/bin/local-openai-infer` — local OpenAI-compatible inference CLI
- `core/engine/tools/local_openai_infer.py` — tool for local inference
- `config/ai_providers.json5` — provider configuration file (user-managed)

## Search Commands

```bash
rg "api/llm" core/engine/routes_integrations.py -n
rg "rest/chat" core/engine/routes_integrations.py -n
rg "llm_service" core/engine/ -l
cat core/engine/llm.py | head -50
```

## Related Features

- `core/features/config-settings-mcp-skills.md`
- `core/features/tts-audio-service.md`
- `core/features/code-executor.md`

## Update Notes

- `config/ai_providers.json5` is user-managed; never overwrite on upgrade without backup
- `POST /api/llm/stop` cancels streaming; ensure cleanup of async generators on stop
