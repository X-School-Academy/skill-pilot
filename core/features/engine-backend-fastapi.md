# Feature Retrieval Index: Engine Backend (FastAPI)

## Retrieval Keywords

engine, FastAPI, backend, Python backend, core/engine, app_factory, main.py, routes, socket_service, scheduler, logger, uv, pyproject.toml, session roots, health check, api/health, SKILL_PILOT_RUNTIME_MODE, production mode, development mode, engine start, engine restart

## Scope

- FastAPI application factory and startup
- Route module organization
- WebSocket and Socket.IO service
- Background scheduler
- Runtime mode (development/production) switching
- Excludes: individual feature routes (each has own feature file)

## Main Behavior

- Engine started via `core/engine/main.py` with uvicorn
- `app_factory.py` creates the FastAPI app instance
- Routes modularized: `routes.py`, `routes_config.py`, `routes_codeware.py`, `routes_integrations.py`, `routes_file_manager.py`
- `socket_service.py` manages WebSocket/Socket.IO connections
- `scheduler.py` manages periodic background tasks
- `GET /api/health` returns health status and timestamp
- `GET /api/session-roots` returns allowed session root paths
- Runtime mode controlled by `SKILL_PILOT_RUNTIME_MODE` env var (`dev`/`prod`)
- Python dependencies managed with `uv` via `pyproject.toml` and `uv.lock`

## Code Map

- `core/engine/main.py` — uvicorn entry point
- `core/engine/app_factory.py` — FastAPI app factory
- `core/engine/routes.py` — primary routes module
- `core/engine/routes_config.py` — config routes
- `core/engine/routes_codeware.py` — codeware routes
- `core/engine/routes_integrations.py` — integration routes
- `core/engine/routes_file_manager.py` — file manager routes
- `core/engine/routes_shared.py` — shared route utilities
- `core/engine/socket_service.py` — WebSocket/Socket.IO
- `core/engine/scheduler.py` — background scheduler
- `core/engine/logger.py` — logging configuration
- `core/engine/settings.py` — settings access
- `core/engine/pyproject.toml` — Python project config
- `core/engine/uv.lock` — locked dependencies

## Search Commands

```bash
cat core/engine/main.py | head -40
cat core/engine/app_factory.py | head -40
cat core/engine/pyproject.toml | head -30
rg "api/health" core/engine/routes.py -n
```

## Related Features

- `core/features/web-terminal-tmux-sessions.md`
- `core/features/auth-session.md`
- `core/features/codeware-dev-mode.md`

## Update Notes

- `uv` is the required Python package manager; do not use pip directly
- Engine restart via `POST /api/codeware/prod/restart` or killing and restarting the process
- `core/engine/data/` stores persistent engine data; back up before migrations
