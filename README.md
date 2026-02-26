# Skill Pilot AI Agent

**An AI-native Codeware system**

> Software runs. Codeware grows.

Skill Pilot is not a traditional application and not a SaaS platform.
It is a **Codeware environment** — a living codebase continuously extended and maintained by AI agents and humans together.

Instead of shipping fixed features, Skill Pilot exposes its own source as the interface.
The AI reads it, modifies it, learns from it, and evolves new capabilities.

**Join Us**

💬 Community: [Discord](https://discord.com/invite/myf9RRhfxN) | [ 𝕏 ](https://x.com/skill_pilot_ai) | [WebChat](assets/webchat-contact.jpg)

## Intro Video

![Intro](assets/intro-video.webp)

---

## What is Codeware?

Traditional computing:

```
Human → UI → Software → Fixed behavior
```

Codeware computing:

```
Human → AI → Codebase → Evolving behavior
```

In Skill Pilot:

* The repository is the product
* Commits become capabilities
* Pull requests become knowledge sharing
* Releases become stabilized intelligence

The system is not "used".
It is **grown**.

---

## Installation

Supported platforms: **macOS**, **Linux**, **Windows via WSL only**

Supported AI agents: **Claude Code**, **Codex**, **Gemini CLI**, **OpenCode** — or bring your own **OpenAI-compatible** or **Claude-compatible** API key

### Auto Install

```bash
curl -fsSL https://raw.githubusercontent.com/x-school-academy/skill-pilot/codeware/install.sh | bash
```

### Manual Install

Follow the step-by-step guide in [SETUP.md](SETUP.md).

---

## Usage

After installation, run:

```bash
./skillpilot.sh help
```

```
Usage: ./skillpilot.sh [help|build|start|stop] [--dev]
       ./skillpilot.sh <enable|disable> <human-detection|live-tts>

Commands:
  help    Show this help message.
  build   Build static webui export (core/webui/www).
  start   Start services. Default command.
  stop    Stop running tmux sessions.
  enable human-detection    Install optional human detection dependencies.
  disable human-detection   Uninstall optional human detection dependencies.
  enable live-tts           Install optional live-tts dependencies.
  disable live-tts          Uninstall optional live-tts dependencies.

Options:
  --dev   Run in development mode (start only).

Defaults:
  - Command defaults to: start
  - Mode defaults to production (without --dev)
```

---

## Your Workspace

After installation, your workspace is organized into focused zones — each one powered by Skill Pilot.

```
skill-pilot/
├── src/                    ← Your commercial-ready product
│   └── ...                    Built end-to-end by Dev Swarm agents
│
└── workspace/
    ├── learning/           ← Your AI study studio
    │   └── ...                Courses, tutorials, and interactive lessons
    │
    ├── projects/           ← Your vibe coding lab
    │   └── ...                Spin up any coding project — fast
    │
    ├── research/           ← Your research workspace
    │   └── ...                Deep dives, analysis, and knowledge gathering
    │
    └── tasks/              ← Your AI task runner
        └── ...                Automate any non-coding task with AI
```

| Zone | What it is |
|------|------------|
| `src/` | The product you are building — from ideas to deployment, managed by Dev Swarm |
| `workspace/learning/` | An AI-powered study studio for courses, tutorials, and skill-building |
| `workspace/projects/` | A vibe coding space — describe what you want, watch it get built |
| `workspace/research/` | A research workspace for analysis, competitive research, and knowledge synthesis |
| `workspace/tasks/` | A task runner for everything else — writing, automation, planning, and more |

> All zones are fully supported by Skill Pilot. Sample workflows for each are coming soon.

---

## Features

**Progress indicator:**

| Symbol | Status |
|--------|--------|
| ⭐⭐⭐⭐⭐ | Ready to use |
| ⭐⭐⭐⭐ | Ready for test |
| ⭐⭐⭐ | Code is ready |
| ⭐⭐ | Wait to open source |
| ⭐ | Planned |

### Core Platform

| Feature | Status |
|---------|--------|
| Skill Pilot Core Engine — Python FastAPI backend with LLM routing, session management, and MCP servers | ⭐⭐⭐⭐⭐ |
| Skill Pilot WebUI — Next.js interface for chat, terminal, workflow editor, course viewer, and settings | ⭐⭐⭐⭐⭐ |
| Multiple AI Code Agent Support — Claude Code, Codex, Gemini CLI, OpenCode CLI | ⭐⭐⭐⭐⭐ |
| LLM API Support — OpenAI-compatible and Claude-compatible API endpoints | ⭐⭐⭐⭐⭐ |
| Background Process Management — tmux-based session lifecycle for long-running agents | ⭐⭐⭐⭐⭐ |
| WebUI Terminal — Full browser-based terminal via WebSocket | ⭐⭐⭐⭐⭐ |

### Agent Skills & Automation

| Feature | Status |
|---------|--------|
| Agent Skill Creator — create and update reusable agent skills via `create-update-agent-skill` | ⭐⭐⭐⭐⭐ |
| Import Agent Skill by Git URL — install third-party skills directly from any git repository | ⭐⭐⭐⭐⭐ |
| Subagent via `use-skill-agent` — run skill-based tasks as a subagent through the core engine | ⭐⭐⭐⭐⭐ |
| New Agent Session via `new-skill-session` — spawn a new agent process in an existing terminal session | ⭐⭐⭐⭐⭐ |
| Agent Skill Schedule Support — cron-based skill scheduling via APScheduler | ⭐⭐⭐⭐⭐ |
| MCP to Skills — expose MCP server tools as callable agent skills | ⭐⭐⭐⭐⭐ |
| Multiple Agent Workflow Diagram Creator & Executor — visual multi-agent workflow editor and runner | ⭐⭐⭐⭐ |

### Development Tools & Extensions

| Feature | Status |
|---------|--------|
| VS Code Extension — IDE integration for Skill Pilot agent control | ⭐⭐⭐⭐⭐ |
| Remote SSH Access via `terminal` MCP — full remote terminal, SCP file transfer, and SSH tunneling | ⭐⭐⭐⭐⭐ |
| Dev Swarm — full software lifecycle from ideas to deployment for building commercial-ready products | ⭐⭐⭐⭐ |
| Chrome Extension — browser integration for Skill Pilot | ⭐⭐⭐⭐ |

### Security

| Feature | Status |
|---------|--------|
| KeySafe Guard via `key-safe` skill — protect and manage LLM API keys in `config/.env` | ⭐⭐⭐⭐⭐ |

### AI Media Generation (via `media` MCP)

| Feature | Status |
|---------|--------|
| ComfyUI Image Generation — text-to-image and image-to-image via ComfyUI workflows | ⭐⭐⭐⭐⭐ |
| ComfyUI Video Generation — text-to-video, image-to-video, and video-to-video workflows | ⭐⭐⭐⭐⭐ |
| ComfyUI LipSync — talking head video from image or video with audio | ⭐⭐⭐⭐⭐ |
| Musetalk Live Avatar — real-time AI avatar powered by MuseTalk | ⭐⭐⭐⭐⭐ |
| MuesTalk LipSync — lip-sync video generation via MuseTalk CLI | ⭐⭐⭐⭐⭐ |
| IndexTTS2 — high-quality speech synthesis via IndexTTS2 | ⭐⭐⭐⭐⭐ |
| SongBloom AI Music Creator — AI music generation with vocals and accompaniment | ⭐⭐⭐⭐⭐ |
| AI Agent Live TTS via `live-tts` MCP — real-time text-to-speech for agent responses | ⭐⭐⭐⭐⭐ |
| GenAI Image Support — generative image tools available to agents | ⭐⭐⭐⭐ |
| GenAI TTS Support — generative text-to-speech tools available to agents | ⭐⭐⭐⭐ |

### Education & Courses

| Feature | Status |
|---------|--------|
| Personal Course Creator — AI-generated interactive courses via LangGraph workflow | ⭐⭐⭐⭐⭐ |
| Tutorial Creator with Realtime Code Execution and AI Assistant — live in-browser code runner with AI feedback | ⭐⭐⭐⭐⭐ |
| Text / Image / Audio / Video Creator — multi-modal content pipeline via LangGraph workflow | ⭐⭐⭐⭐⭐ |

### Desktop Automation & Communication

| Feature | Status |
|---------|--------|
| Screen Recording Skill — record the macOS screen from the CLI via tmux and ffmpeg | ⭐⭐⭐⭐⭐ |
| Screen Drawing Skill — draw temporary bounding-box overlays on macOS for UI highlighting | ⭐⭐⭐⭐⭐ |
| Discord Bot Support — multi-session Discord bot with LLM-powered AI assistant | ⭐⭐⭐⭐⭐ |
| Use Computer Skill — GUI automation via screenshots, mouse control, and keyboard input | ⭐⭐⭐⭐ |

### Smart Home / IoT

| Feature | Status |
|---------|--------|
| Local Security Cameras | ⭐⭐ |
| Z-Wave Smart Home | ⭐⭐ |
| E2EE Security Camera Hub | ⭐⭐ |
| Security Camera Firmware / Cloud Code / Mobile App | ⭐⭐ |

---

## Branch Model

Skill Pilot separates three layers of evolution.

| Branch     | Purpose                           | Who writes            |
|------------|-----------------------------------|-----------------------|
| `codeware` | Stable release layer              | Maintainers           |
| `contrib`  | Shared improvements between users | Community + AI review |
| `user`     | Personal evolving workspace       | User AI               |

### Flow of knowledge

```
codeware  → user        (sync updates)
user      → contrib     (share useful capability)
contrib   → codeware    (stabilized release)
```

Rules:

* `codeware` is protected (release only)
* `contrib` accepts pull requests
* `user` is freely modified by AI
* AI never edits `codeware` directly

---

## How Skill Pilot Works

1. The user runs Skill Pilot locally
2. The AI reads the repository
3. The AI edits code to solve tasks
4. New skills appear as modules
5. Useful skills can be shared to `contrib`
6. Stable knowledge is released to `codeware`

The system improves every time it is used.

---

## Philosophy

Skill Pilot is built on a different assumption:

> Software should not contain all knowledge.
> It should learn knowledge.

Traditional software distributes features.
Codeware distributes capability evolution.

---

## What You Are Installing

You are not installing an application.

You are installing a **habitat for an AI worker**.

The AI does not operate inside the program.
The program operates inside the AI.

---

## Contributing

You do not contribute by writing features for users.
You contribute by teaching the system a reusable skill.

Steps:

1. Work in `user`
2. If multiple users share one computer, each user should fork to a different repo and clone locally to a different path
3. When useful → create PR to `contrib`
4. Maintainers/AI review integration safety
5. Merged into shared knowledge
6. Released into `codeware`

---

## Release Concept

Releases are not feature milestones.

They are **intelligence stabilization points**.

A release means:

> The system has learned enough to be trusted.

---

## License

This project is licensed under the [MIT License](LICENSE).

If you distribute this software, you must keep the copyright and license
information in `LICENSE` unchanged.

Some parts of this project may include open-source code from other sources.
When a source file or folder includes its own `LICENSE`, that license applies
to that code.

---

## Short Definition

Skill Pilot is an AI-native Codeware system where the source code is the interface, commits are capabilities, and software evolves through use.
