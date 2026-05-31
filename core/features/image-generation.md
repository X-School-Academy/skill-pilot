# Feature Retrieval Index: Image Generation

## Retrieval Keywords

image generation, create image, create-image, image service, image_service, gpt_image_2, GPT image, image API, image skill, generate image, image output, picture generation, visual generation

## Scope

- Image generation via AI models (GPT Image 2, etc.)
- Image service in the engine
- `create-image` CLI and skill
- Excludes: ComfyUI-based image generation (see `media-mcp-server.md`)

## Main Behavior

- `core/bin/create-image` CLI generates images from a text prompt
- `image_service.py` provides the image generation service layer
- `gpt_image_2_skill` extension adds GPT Image 2 support
- Generated images stored in `output/` or as returned file paths

## Code Map

- `core/engine/image_service.py` — image generation service
- `core/bin/create-image` — image generation CLI
- `core/skills/system/create-image/` — create-image system skill
- `extensions/gpt_image_2_skill/` — GPT Image 2 skill extension
- `output/` — default output directory for generated images

## Search Commands

```bash
cat core/engine/image_service.py | head -40
find core/skills/system/create-image/ -type f
find extensions/gpt_image_2_skill/ -type f
ls output/ 2>/dev/null
```

## Related Features

- `core/features/media-mcp-server.md`
- `core/features/agent-cli.md`

## Update Notes

- Image provider API key must be set in `config/.env`
- Output directory defaults to `output/`; configurable in `settings.json5`
