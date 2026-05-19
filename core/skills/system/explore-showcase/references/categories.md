# Showcase Categories

A showcase always belongs to exactly one **category**. Each category groups showcases that share an audience focus or subject domain, and defines its own set of **types** (subtypes) in a sibling file under `category-types/`.

When drafting a new showcase:

1. Pick the best-fitting category from the table below.
2. Open `category-types/{category-id}.md` and pick a type within that category.
3. If no category fits, propose a new one — add it to this table AND create `category-types/{new-id}.md`.
4. If the category fits but the type does not, propose a new type inside the matching `category-types/{category-id}.md`.

The `id` column must match an entry in `core/engine/data/showcases.json5`. New categories require both a row here and an entry there.

## Categories

| id | category | scope | types file |
|---|---|---|---|
| `basics` | Basics | Beginner-friendly, low-risk first runs that confirm the environment works end-to-end. | [category-types/basics.md](category-types/basics.md) |
| `browser-tasks` | Browser Tasks | Everyday browser-driven automations. Each one warns about prompt-injection risk before navigating. | [category-types/browser-tasks.md](category-types/browser-tasks.md) |
| `tutorials` | Tutorials | Turn raw material (notes, recordings, videos) into structured learning content. | [category-types/tutorials.md](category-types/tutorials.md) |
| `slides` | Slides | Generate PDF and HTML decks from notes, ideas, or repositories. | [category-types/slides.md](category-types/slides.md) |
| `websites` | Websites | Build, screenshot, iterate, and ship small websites end-to-end. | [category-types/websites.md](category-types/websites.md) |
| `games` | Games | Remake compact open-source games with PixiJS or three.js. | [category-types/games.md](category-types/games.md) |
| `media-generation` | Media Generation | Generate videos, podcasts, talking avatars, and captioned media. | [category-types/media-generation.md](category-types/media-generation.md) |
| `ai-agents` | AI Agents | Progressively deeper agent construction — chatbots, RAG, multi-agent workflows. | [category-types/ai-agents.md](category-types/ai-agents.md) |
| `agent-skills` | Agent Skills | Install, scaffold, and compose Skill Pilot agent skills. | [category-types/agent-skills.md](category-types/agent-skills.md) |
| `mcp-servers` | MCP Servers | Build and audit Model Context Protocol servers and integrations. | [category-types/mcp-servers.md](category-types/mcp-servers.md) |
| `platform-dev` | Platform Dev | Improve Skill Pilot itself: codeware status, worktrees, features, contributions. | [category-types/platform-dev.md](category-types/platform-dev.md) |
| `cloud-gpu` | Cloud & GPU | Cloud and GPU infrastructure fluency: AWS EC2, SSH, RunPod GPUs. | [category-types/cloud-gpu.md](category-types/cloud-gpu.md) |
| `maths` | Maths | Show maths concepts through visible, useful computer-science products (QR codes, Wi-Fi, AI, graphics, encryption). | [category-types/maths.md](category-types/maths.md) |

## How types relate to categories

- A **type** is a recurring shape of showcase within a category — defined by what the user starts with, what the agent does, and what the user ends up with.
- Types are not global. The same surface activity (for example, "generate an image") can be a different type under different categories because the audience and learning goal differ.
- A type entry should include: a one-line definition, the primary audience, a short list of example showcase ideas, and the key skills/extensions/tools used.
