# Skill Pilot Knowledge Points
*Everything you need to know to learn, build, and do real things with AI agents — no coding syntax required.*

---

> ### The Three Stages of Working with AI
>
> | Stage | What It Means | Example |
> |---|---|---|
> | **Vibe Learning** | Pick up just enough basic vocabulary and concepts to guide AI — not to become an expert yourself, but to know what to ask and how to describe what you want. The AI holds the deep knowledge; you learn how to direct it. | *"What is an API key and why do I need one?"* |
> | **Vibe Coding** | Build a real software project by describing what you want — the AI writes, tests, and fixes all the code | *"Build me a personal finance tracker web app"* |
> | **Vibe Doing** | Get real-world tasks done by guiding AI agents with just a few words or one click — no complex setup, no configuration. You say what you want, the agent figures out how and does it. | *"Deploy my app to AWS and send me the live link"* |
>
> **The key insight:** You do not need to learn how to code or become a cloud engineer. You only need to understand concepts well enough to have a clear conversation with the AI. Think of yourself as the director — the AI is the expert doing the work.
>
> You don't need to master all three at once. Start with learning just enough, build something simple, then let the agent do real work for you.

---

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

## 21. Vibe Coding — Projects You Can Build

You don't need to know how to code. Just describe what you want and the agent builds it. Here are real project types students have built with Skill Pilot:

### Personal & Productivity
| Project | What It Is |
|---|---|
| **Personal portfolio website** | A website showing your work, bio, and contact info — deployed live on the internet |
| **Daily journal app** | A private web app to write and search your notes |
| **Habit tracker** | Track daily goals with streaks, charts, and reminders |
| **Personal finance tracker** | Log income and expenses, see charts of where your money goes |
| **Recipe book app** | Store and search your favourite recipes with photos |

### Learning & School
| Project | What It Is |
|---|---|
| **Flashcard study app** | Digital flashcards with spaced repetition, like a personal Anki |
| **Quiz generator** | Paste in any text and get a multiple-choice quiz automatically |
| **Study timer (Pomodoro)** | Focus timer with session tracking and break reminders |
| **School timetable planner** | Visual weekly schedule with subject colour coding |

### Creative & Media
| Project | What It Is |
|---|---|
| **AI image gallery** | Generate images from text and display them in a beautiful gallery |
| **Lyrics-to-song creator** | Turn your lyrics into a real singing audio file |
| **Slideshow video maker** | Combine images and music into a polished video automatically |
| **Talking avatar creator** | Upload a face photo and make it talk with any audio |
| **Podcast transcript tool** | Upload an audio file and get a full searchable transcript |

### Tools & Automation
| Project | What It Is |
|---|---|
| **Discord bot** | A bot that responds to commands, posts updates, or runs mini-games in your server |
| **URL shortener** | Your own personal link shortener like bit.ly |
| **File converter web app** | Drag and drop files to convert between formats (PDF, image, audio, etc.) |
| **Chat with your documents** | Upload PDFs or notes and ask AI questions about them |
| **Local AI chatbot** | Your own private ChatGPT-style chatbot running entirely on your machine |

### Business & Side Projects
| Project | What It Is |
|---|---|
| **Landing page for a product** | A clean, modern product page with sign-up form |
| **Simple e-commerce store** | Product listings, cart, and checkout flow |
| **Booking/appointment system** | Let people book time slots with you online |
| **Content scheduling tool** | Plan and queue social media posts |

---

## 22. Vibe Doing — Real-World Tasks You Can Automate

Vibe doing goes beyond building apps. You guide the agent with a few plain words — or even a single click — and it handles everything: browsing, clicking, uploading, deploying, generating. No configuration. No steps. Just say what outcome you want.

### Content Creation
| Task | What the Agent Does |
|---|---|
| **Create a presentation (slides)** | Takes your bullet points and generates a full slide deck — layout, design, and content included |
| **Generate a PDF report** | Turns your notes or data into a formatted, professional PDF document |
| **Create a short video from text** | Writes a script, generates voiceover, adds visuals, and produces an MP4 video |
| **Create an AI avatar video** | Makes a face image talk and lip-sync to any audio or text you provide |
| **Generate a song from lyrics** | Turns your words into a real vocal singing audio file |
| **Make a slideshow video** | Combines your images with music and transitions into a polished video |
| **Record your screen** | Captures your screen as a video while you work |

### File & Data Tasks
| Task | What the Agent Does |
|---|---|
| **Extract text from audio/video** | Transcribes spoken words into searchable text with timestamps |
| **Analyse an image** | Describes what's in a photo, reads text in images, or answers questions about it |
| **Analyse a video** | Watches a video and answers questions about it or summarises it |
| **Convert and compress media** | Converts files between formats, resizes videos, extracts audio from video |
| **Extract vocals from a song** | Separates the singing voice from the background music in any audio file |
| **Batch rename or organise files** | Renames or sorts hundreds of files automatically based on your rules |

### Web & Research Tasks
| Task | What the Agent Does |
|---|---|
| **Deep research a topic** | Searches the web, reads multiple sources, and writes a structured research report |
| **Scrape and summarise a website** | Visits a URL, reads the content, and gives you a clear summary |
| **Fill out a web form automatically** | Opens a browser and completes a form on your behalf |
| **Take a screenshot of any webpage** | Captures exactly what a webpage looks like at any moment |
| **Monitor a website for changes** | Checks a page on a schedule and alerts you if content changes |

### Cloud & Deployment
| Task | What the Agent Does |
|---|---|
| **Deploy a web app to AWS EC2** | Spins up a cloud server, installs your app, and gives you a live public URL |
| **Set up a cloud server from scratch** | Creates an EC2 instance with all software installed and configured via SSH |
| **Auto-install OpenClaw on EC2** | Runs the full OpenClaw installation on a remote server automatically |
| **Open an SSH tunnel** | Securely connects your local machine to a remote server's port in seconds |
| **Upload files to cloud storage (S3)** | Sends files to AWS S3 bucket storage with a single instruction |
| **Check server status** | Connects to a remote server and reports what's running, disk space, memory usage |

### Communication & Sharing
| Task | What the Agent Does |
|---|---|
| **Post to Discord** | Sends a message, file, or announcement to a Discord channel automatically |
| **Send a webhook notification** | Fires off an HTTP event to trigger other services (e.g., Zapier, Slack, email) |
| **Generate and email a report** | Creates a formatted report and sends it via email or webhook |

### Developer Tasks (Vibe Doing for Builders)
| Task | What the Agent Does |
|---|---|
| **Review code for bugs** | Reads your codebase and finds issues, security risks, and improvements |
| **Write and run tests** | Creates automated tests for your project and runs them, reporting what passed or failed |
| **Commit and push to GitHub** | Stages your changes, writes a commit message, and pushes to your repo |
| **Create a GitHub pull request** | Opens a PR with a proper title and description, ready for review |
| **Publish an npm package** | Bundles and publishes your JavaScript library to the npm registry |
| **Run a headless AI coding agent** | Spawns another AI agent (Claude Code, Gemini CLI, Codex) to work on a task in the background |

---

## 23. Learning Path Suggestion

To go from complete beginner to vibe doing real projects, follow this journey:

### Stage 1 — Vibe Learning (Start Here)
> Goal: learn just enough to talk to AI clearly. You don't need to deeply understand any of this — you only need to know what these things *are* so you can describe what you want.

1. What is an AI agent? What is an LLM? *(so you can pick the right tool)*
2. Tokens, context window, prompts *(so you understand why instructions need to be clear and concise)*
3. What are API keys? *(so you don't accidentally expose secrets)*
4. What is a terminal? What is SSH? *(so you can describe where you want things to run)*
5. What is git and GitHub? *(so you can tell the agent to save and share your work)*
6. What is cloud / AWS / EC2? *(so you can ask the agent to deploy something without confusion)*

### Stage 2 — Vibe Coding (Build Your First Project)
5. Terminal basics — bash, SSH, tmux
6. Version control — git, GitHub, commits, branches
7. Secrets & config — .env, environment variables
8. Package managers — pnpm (frontend), uv (Python backend)
9. Pick a starter project from the list above and build it

### Stage 3 — Vibe Doing (Get Real Things Done)
10. MCP & agent skills — what they are and how to use them
11. Cloud basics — AWS, EC2, SSH tunnels, S3
12. Media AI — TTS, image generation, video creation, ffmpeg
13. Browser automation — Playwright, screenshots, form filling
14. Security awareness — prompt injection, ignore files, least privilege
15. Multi-agent workflows — chaining agents to do complex tasks end to end

---

*Generated: 2026-03-15 | Source: Skill Pilot AI project analysis*
