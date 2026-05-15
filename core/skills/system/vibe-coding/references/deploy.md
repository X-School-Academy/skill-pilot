# Stage Reference: deploy

Deploy a Vibe Coding project locally as launchable software, and deploy to a remote production environment when the project requires it.

## When to Use

- The user asks to deploy the project
- Implementation is ready for deployment
- The project needs a local install/launch path, a remote production release, or both

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implementation.md` and identify deployment target, runtime, and dependencies.

### Step 2: Determine Local and Remote Targets

Every project needs a local deployment because Skill Pilot is an AI operating system: local deployment means installing or packaging the software so the user can launch and operate it from the WebUI dashboard.

If no remote production target is specified in `requirements.md`, `plan.md`, or `implementation.md`, do not invent one. Ask the user how and where to deploy remotely only when remote production deployment is required or requested.

### Step 3: Prepare Local Deployment

Create local deployment support that can be run from the project root. Prefer project-owned commands or scripts, then point dashboard metadata to those commands.

For `workspace/vibe-coding/{project-name}/assets/info.yaml`, use this schema:

```yaml
display_name: Project Display Name
commands:
  start: ""
  dev: ""
  build: ""
  stop: ""
```

Command meanings:

- `start`: launch the locally deployed production-like app
- `dev`: launch the development server or development mode
- `build`: build, package, install, or prepare the local deployable app
- `stop`: stop the locally launched production or development process

Set commands to runnable shell commands from the project root. Leave a command empty only when it truly does not apply or cannot be safely determined.

Common command patterns:

- Node / pnpm app: `start: "pnpm start"`, `dev: "pnpm dev"`, `build: "pnpm build"`, `stop: "pnpm stop"` when a safe stop script exists.
- Node / npm app: `start: "npm start"`, `dev: "npm run dev"`, `build: "npm run build"`, `stop: "npm run stop"` when a safe stop script exists.
- Bun app: `start: "bun start"`, `dev: "bun run dev"`, `build: "bun run build"`, `stop: "bun run stop"` when a safe stop script exists.
- Python / uv app: `start: "uv run python -m <module>"`, `dev: "uv run <dev command>"`, `build: "uv sync --frozen"` or a project package command, `stop: "<project stop command>"` when a safe stop command exists.
- Docker app: `start: "docker compose up -d"`, `dev: "docker compose up"`, `build: "docker compose build"`, `stop: "docker compose down"`.
- Desktop/native app: `build` should package or install it locally, `start` should launch the installed app or executable, and `stop` should close only that app/process.

If the project lacks safe start/stop scripts, add small project-owned scripts or package scripts during deployment. Avoid broad stop commands that may kill unrelated user processes.

### Step 4: Create Dashboard Assets If Missing

Only create dashboard assets during deployment, and only if they do not already exist:

- `workspace/vibe-coding/{project-name}/assets/icon.png`: square raster icon for the WebUI dashboard. Use the `create-image-audio` skill to create it from the project concept when missing.
- `workspace/vibe-coding/{project-name}/assets/info.yaml`: metadata and local deployment commands for the WebUI dashboard.

If `icon.png` already exists, keep it. If `info.yaml` already exists, update only missing or stale deployment fields; preserve user-provided display names and valid custom commands unless they are clearly wrong.

### Step 5: Prepare and Deploy Remote Production If Required

Confirm remote environment requirements, exposed ports, credentials, secrets, domain, and release steps. Use the appropriate tools for the chosen target. Do not assume credentials or infrastructure already exist.

Remote production deployment is separate from local deployment. Even when the target is a remote production server, still complete the local deployment assets and local launch commands first.

### Step 6: Update the Deployment Record

Write `design-docs/deployment.md` (overwrite — it is a living doc):

- What was deployed
- Local deployment commands and launch instructions
- Dashboard assets created or updated
- Remote production target and URL, if any
- Environment / runtime details for local and remote deployment
- Remaining setup items

### Step 7: Update Top-Level Project Files

After a successful deployment, update:

- `README.md` — refresh the Setup, Usage, and any deployment-specific sections (URLs, commands, environment requirements) so users have an accurate operational guide.
- `deployment.md` is already updated in Step 6; no further action needed for `CHANGELOG.md` or `AGENTS.md` in the deploy stage.

### Step 8: Report

Summarize the local deployment outcome, dashboard assets, remote production outcome if applicable, and next steps.
