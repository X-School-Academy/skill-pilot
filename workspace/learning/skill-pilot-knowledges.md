# Skill Pilot Knowledge Points
*Everything you need to know to build an AI agent by vibe coding — no coding syntax required.*

---

## 1. Operating Systems & Platforms

| Keyword | What It Means |
|---|---|
| **Windows** | Microsoft's desktop OS. Most common for everyday users. |
| **macOS** | Apple's desktop OS. Common for developers. |
| **Linux** | Open-source OS widely used on servers and cloud. Many flavors (Ubuntu, Debian, etc.). |
| **WSL / WSL2** | Windows Subsystem for Linux — lets you run Linux commands inside Windows without a virtual machine. |
| **Ubuntu** | A popular Linux flavor, often the default choice for servers and WSL. |
| **Debian** | Another Linux flavor, known for stability. |

---

## 2. Shell & Terminal

| Keyword | What It Means |
|---|---|
| **Terminal** | The text-based window where you type commands. |
| **Shell** | The program that reads your commands. Common ones: bash, zsh, sh. |
| **bash** | The most common shell on Linux. |
| **zsh** | Default shell on macOS. Works like bash with extra features. |
| **CLI** | Command-Line Interface — control software by typing commands instead of clicking. |
| **tmux** | Terminal multiplexer — lets you keep multiple terminal sessions running and switch between them. Essential for long-running background tasks. |
| **sudo** | "Super-user do" — run a command with administrator/root privileges. |
| **SSH** | Secure Shell — a protocol to remotely connect to another computer securely over a network. |
| **SFTP** | Secure File Transfer Protocol — transfer files over SSH. |
| **PTY** | Pseudo-terminal — a software terminal used by programs that need to simulate a real keyboard/screen. |

---

## 3. CLI Tools

| Keyword | What It Means |
|---|---|
| **curl** | Download files or call web APIs from the command line. |
| **wget** | Download files from the internet via command line (similar to curl). |
| **ffmpeg** | Powerful tool for converting, recording, and processing video and audio files. |
| **git** | Version control tool — tracks changes to your code over time. |
| **brew / Homebrew** | The package manager for macOS. Install tools with `brew install <name>`. |
| **apt / apt-get** | The package manager for Debian/Ubuntu Linux. Install tools with `apt install <name>`. |
| **ImageMagick** | CLI tool for editing and converting images. |

---

## 4. Package Managers

| Keyword | What It Means |
|---|---|
| **npm** | Node Package Manager — installs JavaScript/Node.js libraries. Comes with Node.js. |
| **pnpm** | Faster alternative to npm. Uses less disk space. Used for this project's frontend. |
| **pip** | Python's package installer. Install Python libraries with `pip install <name>`. |
| **uv** | A very fast Python package manager and project runner (modern replacement for pip + venv). |
| **Homebrew** | macOS package manager (see CLI Tools above). |
| **apt** | Linux package manager (see CLI Tools above). |

---

## 5. Version Control & Collaboration

| Keyword | What It Means |
|---|---|
| **git** | The tool that tracks every change to your code with a full history. |
| **GitHub** | Website that hosts git repositories online. Enables collaboration and sharing. |
| **GitLab** | Alternative to GitHub, often self-hosted. |
| **Bitbucket** | Another git hosting service (by Atlassian). |
| **branch** | A separate line of development in git — work on features without affecting the main code. |
| **commit** | A saved snapshot of your code changes in git. |
| **pull request (PR)** | A request to merge your branch changes into the main branch — used for code review. |
| **merge** | Combining changes from one branch into another. |
| **fork** | A personal copy of someone else's repository on GitHub. |
| **.gitignore** | A file that tells git which files to ignore (e.g., secrets, build output). |
| **CI/CD** | Continuous Integration / Continuous Deployment — automated pipelines that test and deploy code on every commit. |
| **GitHub Actions** | GitHub's built-in CI/CD automation system. |

---

## 6. Project Configuration Files

| Keyword | What It Means |
|---|---|
| **.env** | A file storing environment variables (secrets, API keys, settings). Never commit to git. |
| **.gitignore** | Tells git which files/folders to skip. |
| **.agentignore** | Tells AI agents which files to skip (sensitive or irrelevant). |
| **.claudeignore** | Claude-specific version of agentignore. |
| **.geminiignore** | Gemini-specific version of agentignore. |
| **.codexignore** | Codex-specific version of agentignore. |
| **CLAUDE.md** | Instructions file that Claude Code reads to understand how to behave in a project. |
| **AGENTS.md** | Similar to CLAUDE.md — project instructions for AI agent tools. |
| **SKILL.md** | Documentation file describing what an agent skill does and how to use it. |
| **package.json** | Node.js project config — lists dependencies, scripts, and metadata. |
| **pyproject.toml** | Python project config — modern replacement for setup.py. |
| **pnpm-lock.yaml** | Lock file for pnpm — records exact dependency versions for reproducibility. |
| **tsconfig.json** | TypeScript configuration file. |
| **JSON** | JavaScript Object Notation — a lightweight data format used for configs and APIs. |
| **JSON5** | A relaxed version of JSON that allows comments and trailing commas. |
| **YAML** | A human-readable data format, commonly used for config files. |
| **Markdown** | Lightweight markup language for writing formatted text (like this file). |
| **JSONL** | JSON Lines — one JSON object per line, often used for streaming data logs. |

---

## 7. Environment & Secrets

| Keyword | What It Means |
|---|---|
| **environment variable** | A named value stored in the OS environment, used to configure software without hardcoding values. |
| **env var** | Short for environment variable. |
| **.env file** | A plain text file that defines environment variables for a project. |
| **API key** | A secret string used to authenticate your app with an external service (e.g., OpenAI, Anthropic). |
| **ANTHROPIC_API_KEY** | The API key for Claude (Anthropic). |
| **OPENAI_API_KEY** | The API key for OpenAI's GPT models. |
| **secret** | Any sensitive value (password, token, key) that must be kept private. |
| **token** | A string that represents authentication credentials or identity. Often short-lived. |
| **SSH key** | A cryptographic key pair used to authenticate SSH connections without passwords. |

---

## 8. Networking & Protocols

| Keyword | What It Means |
|---|---|
| **HTTP / HTTPS** | HyperText Transfer Protocol — the foundation of web communication. S = Secure (encrypted). |
| **REST API** | Representational State Transfer — a standard style for building web APIs using HTTP. |
| **WebSocket** | A protocol for two-way, real-time communication between browser and server. |
| **port** | A numbered channel on a computer for network communication (e.g., port 3000 for a web server). |
| **port forwarding** | Redirecting traffic from one port/machine to another. Common in SSH tunneling. |
| **SSH tunnel** | Using SSH to securely forward network traffic through an encrypted channel. |
| **webhook** | A URL that receives HTTP POST requests when an event happens (e.g., payment completed). |
| **OAuth** | Open Authorization — a protocol that lets apps access user data from other services without passwords. |
| **localhost** | Refers to your own computer in network terms (IP: 127.0.0.1). |

---

## 9. AI & LLM Concepts

| Keyword | What It Means |
|---|---|
| **LLM** | Large Language Model — an AI trained on vast text to understand and generate language (e.g., GPT-4, Claude). |
| **AI agent** | An LLM that can take actions (call tools, browse web, run code) to complete tasks autonomously. |
| **agent skill** | A packaged, reusable instruction set that teaches an AI agent how to perform a specific task. |
| **prompt** | The text input you give to an LLM to direct its response. |
| **system prompt** | A special prompt that sets the AI's overall behavior and role before the conversation begins. |
| **token** | The unit of text an LLM processes (roughly 1 word ≈ 1–2 tokens). Affects cost and limits. |
| **context window** | The maximum number of tokens an LLM can see at once (both input + output). |
| **LLM cache** | Caching repeated prompt prefixes to avoid reprocessing — reduces latency and cost. |
| **streaming** | Receiving LLM output word-by-word in real time instead of waiting for the full response. |
| **tool calling / function calling** | An LLM's ability to call defined tools/functions (e.g., search web, run code) as part of its response. |
| **RAG** | Retrieval-Augmented Generation — fetching relevant documents and feeding them to an LLM so it can answer questions about private or recent data. |
| **embedding** | A numeric vector representing text — used for semantic search and similarity comparisons. |
| **multi-agent** | A system where multiple AI agents collaborate, each handling different subtasks. |
| **vibe coding** | Using natural language with AI tools to build software without writing code manually. |
| **chat completion** | The API call that sends messages to an LLM and receives a response. |

---

## 10. MCP (Model Context Protocol)

| Keyword | What It Means |
|---|---|
| **MCP** | Model Context Protocol — a standard protocol for connecting AI models to external tools and data sources. |
| **MCP server** | A small service that exposes tools (functions) an LLM can call via MCP. |
| **MCP tool** | A callable function registered on an MCP server (e.g., open browser, run command, search files). |
| **FastMCP** | A Python framework for building MCP servers quickly. |
| **Claude Code** | Anthropic's official CLI that uses Claude as a coding assistant in your terminal. |

---

## 11. AI Model Providers & Services

| Keyword | What It Means |
|---|---|
| **Anthropic** | The company behind Claude AI models. |
| **Claude** | Anthropic's family of AI models (Claude 3, Claude 4, etc.). |
| **OpenAI** | The company behind GPT models and the ChatGPT service. |
| **GPT** | OpenAI's series of language models (GPT-3.5, GPT-4, etc.). |
| **Google Gemini** | Google's family of AI models. |
| **GitHub Copilot** | AI coding assistant built into code editors, powered by OpenAI. |
| **Codex** | OpenAI's code-focused model, also the name of OpenAI's CLI agent. |
| **Ollama** | A tool to run LLMs locally on your own machine (offline, private). |
| **OpenRouter** | A service that provides a single API to access many different LLMs. |
| **HuggingFace** | A platform hosting open-source AI models and datasets. |

---

## 12. Backend Frameworks & Tools

| Keyword | What It Means |
|---|---|
| **Python** | A popular, easy-to-learn programming language widely used in AI/ML and backend development. |
| **Node.js** | A JavaScript runtime that lets you run JavaScript on the server (outside the browser). |
| **FastAPI** | A fast Python web framework for building APIs. |
| **Uvicorn** | A fast web server that runs FastAPI and other Python async apps. |
| **asyncio** | Python's built-in library for writing asynchronous (non-blocking) code. |
| **WebSocket server** | A server that maintains persistent two-way connections with clients. |
| **Socket.io** | A library for real-time bidirectional communication between browser and server. |

---

## 13. Frontend Frameworks & Libraries

| Keyword | What It Means |
|---|---|
| **Next.js** | A React framework for building full-stack web apps with server-side rendering and routing. |
| **React** | A JavaScript library for building interactive user interfaces. |
| **TypeScript** | JavaScript with type annotations — catches errors before running. |
| **Tailwind CSS** | A utility-first CSS framework — style by adding class names rather than writing custom CSS. |
| **Mantine** | A React UI component library with ready-made components (buttons, modals, inputs, etc.). |
| **Redux** | A state management library for React apps — stores shared app data centrally. |
| **xterm.js** | A browser-based terminal emulator — renders a real terminal in a web page. |
| **CodeMirror** | A browser-based code editor component with syntax highlighting. |

---

## 14. Cloud & Infrastructure

| Keyword | What It Means |
|---|---|
| **AWS** | Amazon Web Services — the world's largest cloud computing platform. |
| **EC2** | AWS Elastic Compute Cloud — virtual machines you rent in the cloud. |
| **S3** | AWS Simple Storage Service — cloud object/file storage. |
| **AWS CLI** | Command-line tool to control AWS services. |
| **VPC** | Virtual Private Cloud — an isolated private network within AWS. |
| **IAM** | AWS Identity and Access Management — controls who can do what in AWS. |
| **Docker** | A tool that packages an app and all its dependencies into a portable container. |
| **Docker Compose** | A tool to define and run multi-container Docker applications. |
| **container** | A lightweight, isolated environment for running software consistently anywhere. |

---

## 15. Media & AI Media Processing

| Keyword | What It Means |
|---|---|
| **TTS** | Text-to-Speech — AI that converts written text into spoken audio. |
| **STT / Whisper** | Speech-to-Text — AI that transcribes spoken audio to text. OpenAI's Whisper is a popular model. |
| **image generation** | AI creating images from text descriptions (e.g., DALL-E, Stable Diffusion). |
| **vision model** | An LLM that can also understand images (e.g., GPT-4o, Claude 3). |
| **video generation** | AI creating short video clips from text or images. |
| **lip-sync** | AI technology that animates a face video to match audio speech. |
| **Demucs** | AI tool for separating vocals from music in audio files. |
| **ComfyUI** | A visual workflow builder for running AI image/video generation pipelines. |
| **GPU** | Graphics Processing Unit — hardware essential for training and running AI models fast. |
| **CUDA** | NVIDIA's framework for running computations on GPU — required for many AI tools. |

---

## 16. Browser Automation & Testing

| Keyword | What It Means |
|---|---|
| **Playwright** | A library that controls browsers programmatically — automate clicks, form fills, screenshots, etc. |
| **headed mode** | Running a browser automation with the browser window visible. |
| **headless mode** | Running a browser automation without any visible window (background). |
| **screenshot** | Capturing the current state of a browser page as an image. |
| **PyAutoGUI** | Python library to automate mouse and keyboard actions on the desktop. |

---

## 17. Communication & Integrations

| Keyword | What It Means |
|---|---|
| **Discord** | A messaging platform. Bots can be created to automate messages and commands. |
| **webhook** | See Networking section. |
| **ONVIF** | An open standard protocol for controlling IP security cameras. |
| **WebRTC** | Web Real-Time Communication — protocol for peer-to-peer audio/video/data in browsers. |

---

## 18. Security Concepts

| Keyword | What It Means |
|---|---|
| **API key** | Secret credential for accessing an external API (see Environment & Secrets). |
| **secret management** | Safely storing and accessing secrets (keys, passwords) without exposing them in code. |
| **prompt injection** | An attack where malicious text in a webpage or document tries to hijack an AI agent's behavior. |
| **ignore files** | Files like .gitignore, .agentignore that prevent sensitive files from being read or committed. |
| **principle of least privilege** | Give processes/users only the minimum permissions they need. |
| **SSH keys** | Cryptographic keys used for passwordless, secure remote access. |
| **token expiry** | API tokens that expire after a set time for security — you must refresh them. |

---

## 19. Project Architecture Patterns

| Keyword | What It Means |
|---|---|
| **monorepo** | Keeping multiple related projects (frontend, backend, tools) in one git repository. |
| **microservices** | Breaking an app into small, independent services that communicate via APIs. |
| **client-server** | Architecture where clients (browsers, apps) make requests to a central server. |
| **async / await** | A programming pattern for handling tasks that take time (network calls, file I/O) without blocking. |
| **event-driven** | Architecture where actions are triggered by events (messages, clicks, data changes). |
| **plugin / extension system** | Architecture that allows third-party code to be added without modifying the core. |
| **workflow** | A defined sequence of steps executed in order, often as a JSON file in this project. |

---

## 20. Key Files & Naming Conventions (Skill Pilot Specific)

| Keyword | What It Means |
|---|---|
| **SKILL.md** | Describes what an agent skill does, its inputs, and outputs. |
| **plan.md** | A development plan file used by Skill Pilot to guide implementation. |
| **ideas.md** | Captures project ideas and configuration (like `src_root`). |
| **update.md** | Describes changes needed for an existing feature. |
| **issues.md** | Lists known bugs or problems to fix in a feature. |
| **implement.md** | Documents how a feature was implemented. |
| **user_preferences.md** | Stores user-specific workflow preferences for the AI to follow. |
| **MEMORY.md** | An index of the AI agent's persistent memory files across conversations. |
| **REFERENCE.md** | Reference documentation for a skill or module. |
| **workspace/** | The working area where user projects, learning materials, and tasks live. |
| **core/** | The platform core — engine, web UI, built-in skills, MCP servers. |
| **dev-swarm/** | Development workflow skills and configurations. |

---

## 21. Learning Path Suggestion

To build an AI agent project from zero (vibe coding approach), learn these in order:

1. **Terminal basics** → bash, SSH, tmux
2. **Version control** → git, GitHub, .gitignore, branches, commits
3. **Secrets & config** → .env, environment variables, API keys
4. **Package managers** → npm/pnpm (frontend), pip/uv (Python backend)
5. **AI fundamentals** → LLM, token, context window, prompt, tool calling
6. **MCP & agents** → MCP server, MCP tool, agent skill, multi-agent
7. **Backend basics** → REST API, WebSocket, HTTP, FastAPI/Node.js
8. **Frontend basics** → Next.js, React, Tailwind CSS
9. **Cloud & infra** → AWS, EC2, Docker, SSH tunnel
10. **Media AI** → TTS, vision model, image generation, ffmpeg
11. **Security** → prompt injection, secret management, ignore files

---

*Generated: 2026-03-15 | Source: Skill Pilot AI project analysis*
