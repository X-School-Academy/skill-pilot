# Feature Retrieval Index: Extensions System

## Retrieval Keywords

extensions, extension, skill-pilot-extension, install extension, extension action, extension static files, extensions config, extensions API, third-party extension, community extension, extension directory, extensions/

## Scope

- Extension installation, listing, and action execution
- Static file serving for extensions
- Extension management UI in config page
- Bundled extensions: Scrapling, ComfyUI nodes, chrome, live-avatar, vibe-kanban, graphify, hyperframes, etc.
- Excludes: individual extension feature details (each is its own area)

## Main Behavior

- `GET /api/config/extensions` lists installed extensions
- `POST /api/config/extensions/action` executes an extension action (install, uninstall, update)
- `GET /api/config/extensions/{dir_name}/static` serves extension static assets
- Extensions live under `extensions/` directory
- `skill-pilot-extension` skill manages extension lifecycle

## Code Map

- `core/engine/routes_config.py` — `/api/config/extensions*` route handlers
- `extensions/` — all extensions directory
- `extensions/Scrapling/` — web scraping extension
- `extensions/comfyui-autocropfaces-2/` — ComfyUI face crop node
- `extensions/comfyui-videohelpersuite/` — ComfyUI video helper nodes
- `extensions/comfyui-was-node-suite/` — ComfyUI WAS node suite
- `extensions/comfyui_gfpgan/` — ComfyUI GFPGAN node
- `extensions/comfyui-terminal/` — ComfyUI terminal node
- `extensions/chrome/` — Chrome extension
- `extensions/chrome-devtool-proxy/` — Chrome DevTools proxy
- `extensions/live-avatar/` — live avatar extension
- `extensions/vibe-kanban/` — Vibe Kanban board
- `extensions/graphify/` — graph visualization extension
- `extensions/hyperframes/` — hyperframes extension
- `extensions/gpt_image_2_skill/` — GPT Image 2 skill
- `extensions/docker/` — Docker configuration
- `extensions/advertising-skills/` — advertising skills
- `extensions/garden-skills/` — garden skills
- `extensions/marketingskills/` — marketing skills
- `extensions/seo-geo-skills/` — SEO/GEO skills
- `extensions/prompt-optimizer/` — prompt optimization
- `extensions/research/` — research extension
- `extensions/video-use/` — video use extension
- `extensions/gitnexus/` — git nexus extension
- `extensions/threejs-skill/` — Three.js skill
- `extensions/awesome-design-md/` — design markdown
- `core/skills/system/skill-pilot-extension/` — extension management skill

## Search Commands

```bash
rg "api/config/extensions" core/engine/routes_config.py -n
ls extensions/
find core/skills/system/skill-pilot-extension/ -type f
```

## Related Features

- `core/features/config-settings-mcp-skills.md`
- `core/features/skill-agent-system.md`
- `core/features/media-mcp-server.md`

## Update Notes

- Extensions are gitmodules or local directories; check `.gitmodules` for submodule details
- Extension static assets served from `extensions/{dir_name}/` path
