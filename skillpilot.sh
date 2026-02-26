#!/usr/bin/env bash

set -euo pipefail

reload_shell_env() {
  export PATH="$HOME/.local/bin:$PATH"
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) export PNPM_HOME="${PNPM_HOME:-$HOME/Library/pnpm}" ;;
    *) export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}" ;;
  esac
  export PATH="$PNPM_HOME:$PATH"

  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi

  hash -r 2>/dev/null || true
}

reload_shell_env

if ! command -v tmux >/dev/null 2>&1; then
  echo "Error: tmux is not installed."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_ENV_FILE="${ROOT_DIR}/config/.env"
ACTION="start"
IS_DEV=0
AVAILABLE_PROVIDERS=()

print_help() {
  cat <<'EOF_HELP'
Usage: ./skillpilot.sh [help|build|start|stop] [--dev]

Commands:
  help    Show this help message.
  build   Build static webui export (core/webui/www).
  start   Start services. Default command.
  stop    Stop running tmux sessions.

Options:
  --dev   Run in development mode.

Defaults:
  - Command defaults to: start
  - Mode defaults to production (without --dev)
EOF_HELP
}

parse_args() {
  local action_set=0
  while (($# > 0)); do
    case "$1" in
      --dev)
        IS_DEV=1
        ;;
      help|-h|--help|build|start|stop)
        if ((action_set == 1)); then
          echo "Error: multiple commands provided."
          print_help
          exit 1
        fi
        ACTION="$1"
        action_set=1
        ;;
      *)
        echo "Error: unknown argument '$1'."
        print_help
        exit 1
        ;;
    esac
    shift
  done
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Error: ${cmd} is required."
    exit 1
  fi
}

ensure_webui_deps() {
  require_cmd pnpm
  if [[ ! -d "${ROOT_DIR}/core/webui/node_modules" ]]; then
    echo "core/webui/node_modules missing, running pnpm install..."
    pnpm -C "${ROOT_DIR}/core/webui" install
  fi
}

ensure_engine_venv() {
  require_cmd uv
  if [[ ! -d "${ROOT_DIR}/core/engine/.venv" ]]; then
    echo "core/engine/.venv missing, running uv sync..."
    if ! uv --project "${ROOT_DIR}/core/engine" sync; then
      echo "Error: uv sync failed."
      if [[ "$(uname -s)" == "Linux" ]]; then
        local prefix=""
        if [[ "$(id -u)" -ne 0 ]] && command -v sudo >/dev/null 2>&1; then
          prefix="sudo "
        fi
        echo "Likely cause: missing PortAudio development headers for pyaudio (portaudio.h)."
        if command -v apt-get >/dev/null 2>&1; then
          echo "Install dependency:"
          echo "  ${prefix}apt-get update && ${prefix}apt-get install -y portaudio19-dev"
        elif command -v dnf >/dev/null 2>&1; then
          echo "Install dependency:"
          echo "  ${prefix}dnf install -y portaudio-devel"
        else
          echo "Install the OS package that provides portaudio.h, then retry."
        fi
      fi
      echo "After installing dependencies, run:"
      echo "  uv --project ${ROOT_DIR}/core/engine sync"
      exit 1
    fi
  fi
}

engine_python() {
  local py="${ROOT_DIR}/core/engine/.venv/bin/python"
  if [[ -x "${py}" ]]; then
    echo "${py}"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  echo "Error: python3 is required." >&2
  exit 1
}

ask_yes_no() {
  local prompt="$1"
  local default_no="${2:-1}"
  local answer=""
  while true; do
    if [[ "${default_no}" == "0" ]]; then
      read -r -p "${prompt} [Y/n]: " answer
      answer="${answer:-y}"
    else
      read -r -p "${prompt} [y/N]: " answer
      answer="${answer:-n}"
    fi
    case "${answer}" in
      y|Y|yes|YES|Yes)
        return 0
        ;;
      n|N|no|NO|No)
        return 1
        ;;
      *)
        echo "Please answer y or n."
        ;;
    esac
  done
}

port_available() {
  local host="$1"
  local port="$2"
  local py
  py="$(engine_python)"
  "${py}" - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind((host, port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
raise SystemExit(0)
PY
}

pick_port() {
  local label="$1"
  local host="$2"
  local suggested="$3"
  local blocked_port="${4:-}"
  local chosen=""

  while true; do
    read -r -p "${label} port [${suggested}]: " chosen
    chosen="${chosen:-${suggested}}"

    if [[ ! "${chosen}" =~ ^[0-9]+$ ]] || ((chosen < 1 || chosen > 65535)); then
      echo "Invalid port '${chosen}'. Enter a number between 1 and 65535."
      continue
    fi

    if [[ -n "${blocked_port}" && "${chosen}" == "${blocked_port}" ]]; then
      echo "Port ${chosen} is already used by another Skill Pilot service."
      continue
    fi

    if port_available "${host}" "${chosen}"; then
      echo "${chosen}"
      return
    fi

    echo "Port ${chosen} is not available on ${host}."
  done
}

generate_uuid() {
  local py
  py="$(engine_python)"
  "${py}" - <<'PY'
import uuid
print(uuid.uuid4())
PY
}

choose_provider() {
  local choice=""
  local i=1

  echo "Detected available CLI providers:"
  for provider in "${AVAILABLE_PROVIDERS[@]}"; do
    echo "  ${i}. ${provider}"
    ((i += 1))
  done

  while true; do
    read -r -p "Select default LLM provider [1]: " choice
    choice="${choice:-1}"
    if [[ "${choice}" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#AVAILABLE_PROVIDERS[@]})); then
      echo "${AVAILABLE_PROVIDERS[$((choice - 1))]}"
      return
    fi
    echo "Invalid selection. Enter a number from 1 to ${#AVAILABLE_PROVIDERS[@]}."
  done
}

update_settings_json5() {
  local host="$1"
  local webui_port="$2"
  local engine_port="$3"
  local py
  py="$(engine_python)"

  "${py}" - "${ROOT_DIR}/config/settings.json5" "${host}" "${webui_port}" "${engine_port}" <<'PY'
import json
import sys
from pathlib import Path

import json5

settings_path = Path(sys.argv[1])
host = sys.argv[2]
webui_port = int(sys.argv[3])
engine_port = int(sys.argv[4])

if settings_path.is_file():
    data = json5.loads(settings_path.read_text(encoding="utf-8"))
else:
    data = {}

if not isinstance(data, dict):
    data = {}

services = data.setdefault("services", {})
if not isinstance(services, dict):
    services = {}
    data["services"] = services

webui = services.setdefault("webui", {})
if not isinstance(webui, dict):
    webui = {}
    services["webui"] = webui
webui["host"] = host
webui["port"] = webui_port

engine = services.setdefault("engine", {})
if not isinstance(engine, dict):
    engine = {}
    services["engine"] = engine
engine["host"] = host
engine["port"] = engine_port

settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

update_ai_providers_json5() {
  local provider_id="$1"
  local py
  py="$(engine_python)"

  "${py}" - "${ROOT_DIR}/config/ai_providers.json5" "${provider_id}" <<'PY'
import json
import sys
from pathlib import Path

import json5

providers_path = Path(sys.argv[1])
default_provider = sys.argv[2]

data = json5.loads(providers_path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit("Invalid ai_providers.json5 format")

defaults = data.setdefault("default", {})
if not isinstance(defaults, dict):
    defaults = {}
    data["default"] = defaults
defaults["llm"] = default_provider

llm = data.get("llm", [])
if isinstance(llm, list):
    for item in llm:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        item["disabled"] = item_id != default_provider

providers_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

write_engine_env() {
  local only_allow_https="$1"
  local auth_token="$2"
  local api_type="$3"
  local api_url="$4"
  local api_key="$5"

  {
    echo "ONLY_ALLOW_HTTPS=${only_allow_https}"
    echo "AUTH_TOKEN=${auth_token}"
    case "${api_type}" in
      anthropic)
        echo "ANTHROPIC_BASE_URL=${api_url}"
        echo "ANTHROPIC_AUTH_TOKEN=${api_key}"
        echo "ANTHROPIC_API_KEY="
        ;;
      openai)
        echo "OPENAI_BASE_URL=${api_url}"
        echo "OPENAI_API_KEY=${api_key}"
        ;;
      *)
        ;;
    esac
  } > "${ENGINE_ENV_FILE}"

  chmod 600 "${ENGINE_ENV_FILE}" 2>/dev/null || true
}

detect_available_providers() {
  AVAILABLE_PROVIDERS=()

  if command -v claude >/dev/null 2>&1; then
    AVAILABLE_PROVIDERS+=("claude")
  fi
  if command -v codex >/dev/null 2>&1; then
    AVAILABLE_PROVIDERS+=("codex")
  fi
  if command -v gemini >/dev/null 2>&1; then
    AVAILABLE_PROVIDERS+=("gemini")
  fi
  if command -v opencode >/dev/null 2>&1; then
    AVAILABLE_PROVIDERS+=("opencode")
  fi
}

maybe_install_cli_tools() {
  local installed_any=1

  if ask_yes_no "Install Claude Code CLI now with: curl -fsSL https://claude.ai/install.sh | bash?" 1; then
    if curl -fsSL https://claude.ai/install.sh | bash; then
      installed_any=0
    else
      echo "Claude installer failed."
    fi
  fi

  if command -v brew >/dev/null 2>&1; then
    if ask_yes_no "Install OpenAI Codex CLI now with: brew install codex?" 1; then
      if brew install codex; then
        installed_any=0
      else
        echo "brew install codex failed."
      fi
    fi
  else
    echo "Homebrew is not available, skipping 'brew install codex'."
  fi

  return "${installed_any}"
}

run_init_wizard_if_needed() {
  if [[ -f "${ENGINE_ENV_FILE}" ]]; then
    return
  fi

  echo "config/.env not found. Running first-time initialization."
  echo ""
  echo "This setup will ask a few questions to prepare Skill Pilot."
  echo "Each step explains what it changes and why it is needed."
  echo ""

  local listen_host only_allow_https
  local webui_port engine_port
  local provider_id=""
  local selected_cli_provider=""
  local api_type="none"
  local api_url=""
  local api_key=""
  local webui_auth_token

  echo "Step 1/6 - Network host"
  echo "What: choose where Skill Pilot listens for connections."
  echo "Why: 127.0.0.1 keeps access on this computer only and is safest."
  read -r -p "Listen host [127.0.0.1]: " listen_host
  listen_host="${listen_host:-127.0.0.1}"

  only_allow_https=0
  if [[ "${listen_host}" != "127.0.0.1" && "${listen_host}" != "localhost" ]]; then
    echo ""
    echo "You selected a non-local host."
    echo "What: decide whether plain HTTP is allowed."
    echo "Why: allowing HTTP makes setup easier but traffic is not encrypted."
    if ask_yes_no "Host is ${listen_host}. Allow HTTP access without HTTPS for all clients?" 1; then
      only_allow_https=0
    else
      only_allow_https=1
    fi
  fi

  echo ""
  echo "Step 2/6 - Service ports"
  echo "What: choose ports for WebUI and Core Engine."
  echo "Why: each service needs an open port; defaults are 3000 and 3001."
  webui_port="$(pick_port "WebUI" "${listen_host}" "3000")"
  engine_port="$(pick_port "Core engine" "${listen_host}" "3001" "${webui_port}")"

  local local_token=""
  echo ""
  echo "Step 3/6 - AI tool detection"
  echo "What: check if Claude, Codex, Gemini, or OpenCode CLI is installed."
  echo "Why: Skill Pilot needs one of them as the default coding agent."
  detect_available_providers

  if ((${#AVAILABLE_PROVIDERS[@]} == 0)); then
    echo "No supported AI code agent CLI found (claude/codex/gemini/opencode)."
    if ask_yes_no "Do you have an OpenAI-compatible or Claude-compatible API URL and key?" 1; then
      echo ""
      echo "Step 4/6 - Optional CLI install"
      echo "What: offer to install Claude and/or Codex CLI automatically."
      echo "Why: if no CLI exists, Skill Pilot cannot run coding-agent tasks."
      maybe_install_cli_tools || true
      detect_available_providers
    fi
  fi

  if ((${#AVAILABLE_PROVIDERS[@]} == 0)); then
    echo "No AI code agent CLI is available, and setup cannot continue automatically."
    echo "Please re-run this script after installing an agent, or follow SETUP.md for manual setup."
    return 1
  fi

  selected_cli_provider="$(choose_provider)"
  provider_id="${selected_cli_provider}"
  echo ""
  echo "Step 5/6 - API endpoint (optional)"
  echo "What: configure your API URL and key for compatible providers."
  echo "Why: required when using custom OpenAI-compatible or Claude-compatible endpoints."

  case "${selected_cli_provider}" in
    claude)
      if ask_yes_no "Configure Claude-compatible API URL and key now?" 1; then
        api_type="anthropic"
        provider_id="claude-compat"
      fi
      ;;
    codex)
      if ask_yes_no "Configure OpenAI-compatible API URL and key now?" 1; then
        api_type="openai"
        provider_id="codex-compat"
      fi
      ;;
    opencode)
      if ask_yes_no "Configure OpenAI-compatible API URL and key now?" 1; then
        api_type="openai"
      fi
      ;;
    gemini)
      api_type="none"
      ;;
  esac

  if [[ "${api_type}" == "anthropic" ]]; then
    read -r -p "Claude-compatible API URL: " api_url
    while [[ -z "${api_url}" ]]; do
      echo "API URL is required."
      read -r -p "Claude-compatible API URL: " api_url
    done
    read -r -s -p "Claude-compatible API key/token: " api_key
    echo ""
    while [[ -z "${api_key}" ]]; do
      echo "API key/token is required."
      read -r -s -p "Claude-compatible API key/token: " api_key
      echo ""
    done
  elif [[ "${api_type}" == "openai" ]]; then
    read -r -p "OpenAI-compatible API URL: " api_url
    while [[ -z "${api_url}" ]]; do
      echo "API URL is required."
      read -r -p "OpenAI-compatible API URL: " api_url
    done
    read -r -s -p "OpenAI-compatible API key: " api_key
    echo ""
    while [[ -z "${api_key}" ]]; do
      echo "API key is required."
      read -r -s -p "OpenAI-compatible API key: " api_key
      echo ""
    done
  fi

  echo ""
  echo "Step 6/6 - WebUI auth token"
  echo "What: set a token used by the web interface for access control."
  echo "Why: this prevents unauthorized use of your local/remote instance."
  webui_auth_token="$(generate_uuid)"
  read -r -p "WebUI auth token [${webui_auth_token}]: " local_token
  webui_auth_token="${local_token:-${webui_auth_token}}"

  write_engine_env "${only_allow_https}" "${webui_auth_token}" "${api_type}" "${api_url}" "${api_key}"
  update_settings_json5 "${listen_host}" "${webui_port}" "${engine_port}"
  update_ai_providers_json5 "${provider_id}"

  echo "Initialization completed:"
  echo "  - ${ENGINE_ENV_FILE} created"
  echo "  - config/settings.json5 updated"
  echo "  - config/ai_providers.json5 default provider set to '${provider_id}'"
}

build_webui_export() {
  ensure_webui_deps
  echo "Building static webui export..."
  pnpm -C "${ROOT_DIR}/core/webui" export
}

ensure_webui_release_assets() {
  local webui_www_dir="${ROOT_DIR}/core/webui/www"
  local webui_index="${webui_www_dir}/index.html"
  if [[ ! -f "${webui_index}" ]]; then
    echo "Error: missing WebUI release assets at ${webui_www_dir}."
    echo "Run './skillpilot.sh build' first, or commit core/webui/www for release startup."
    exit 1
  fi
}

load_guarded_env() {
  if [[ ! -f "${ENGINE_ENV_FILE}" ]]; then
    return
  fi

  local env_content=""
  if [[ -r "${ENGINE_ENV_FILE}" ]]; then
    env_content="$(cat "${ENGINE_ENV_FILE}")"
  else
    echo "Loading protected env from ${ENGINE_ENV_FILE} (sudo required)..."
    sudo -k
    env_content="$(sudo cat -- "${ENGINE_ENV_FILE}")"
    sudo -k
  fi

  local parser_python
  parser_python="$(engine_python)"

  local loaded_keys=()
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    export "${key}=${value}"
    loaded_keys+=("${key}")
  done < <(printf '%s' "${env_content}" | "${parser_python}" -c '
from io import StringIO
import sys
try:
    from dotenv import dotenv_values
except Exception as exc:
    print(f"Error: python-dotenv is required to parse .env ({exc})", file=sys.stderr)
    raise SystemExit(2)
values = dotenv_values(stream=StringIO(sys.stdin.read()))
for key, value in values.items():
    if isinstance(key, str) and isinstance(value, str):
        sys.stdout.write(key)
        sys.stdout.write("\0")
        sys.stdout.write(value)
        sys.stdout.write("\0")
')

  export IN_KEYS_SAFE_GUARD=1
  loaded_keys+=("IN_KEYS_SAFE_GUARD")
  if ((${#loaded_keys[@]} > 0)); then
    local key_csv
    key_csv="$(IFS=,; echo "${loaded_keys[*]}")"
    export SAFE_DOTENV_UNSET_KEYS="${key_csv}"
  fi
}


get_webui_base_url() {
  local mode="$1"
  local py
  py="$(engine_python)"
  "${py}" - "${ROOT_DIR}/config/settings.json5" "${mode}" <<'PY'
import sys
from pathlib import Path
try:
    import json5
    data = json5.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    data = {}
services = data.get("services", {}) if isinstance(data, dict) else {}
if sys.argv[2] == "dev":
    svc = services.get("webui", {}) if isinstance(services, dict) else {}
    default_port = "3000"
else:
    svc = services.get("engine", {}) if isinstance(services, dict) else {}
    default_port = "3001"
host = str(svc.get("host", "127.0.0.1")) if isinstance(svc, dict) else "127.0.0.1"
port = str(svc.get("port", default_port)) if isinstance(svc, dict) else default_port
print(f"http://{host}:{port}/")
PY
}

has_gui_env() {
  local os_type
  os_type="$(uname -s 2>/dev/null)"
  if [[ "${os_type}" == "Darwin" ]]; then
    # macOS: no GUI only when inside an SSH session without X11 forwarding
    if [[ -n "${SSH_TTY:-}" || -n "${SSH_CLIENT:-}" ]] && [[ -z "${DISPLAY:-}" ]]; then
      return 1
    fi
    return 0
  else
    # Linux/other: GUI requires DISPLAY or WAYLAND_DISPLAY
    [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]
  fi
}

open_in_browser() {
  local url="$1"
  if [[ "$(uname -s 2>/dev/null)" == "Darwin" ]]; then
    open "${url}" 2>/dev/null || true
  else
    xdg-open "${url}" 2>/dev/null || true
  fi
}

open_or_print_webui_url() {
  local mode="$1"
  local base_url url
  base_url="$(get_webui_base_url "${mode}")"
  if [[ -n "${AUTH_TOKEN:-}" ]]; then
    url="${base_url}?token=${AUTH_TOKEN}"
  else
    url="${base_url}"
  fi
  echo ""
  if has_gui_env; then
    echo "Prepare to launch browser in 2 seconds: ${base_url}"
    sleep 2
    echo "Opening WebUI in browser: ${base_url}"
    open_in_browser "${url}"
  else
    echo "WebUI ready. Open this URL in your browser:"
    echo "  ${url}"
  fi
}

start_session() {
  local session_name="$1"
  local command="$2"

  if tmux has-session -t "${session_name}" 2>/dev/null; then
    echo "Session '${session_name}' already exists. Skipping."
    return
  fi

  tmux new-session -d -s "${session_name}" "cd '${ROOT_DIR}' && ${command}"
  echo "Started session '${session_name}'."
}

stop_session() {
  local session_name="$1"

  if ! tmux has-session -t "${session_name}" 2>/dev/null; then
    echo "Session '${session_name}' does not exist. Skipping."
    return
  fi

  tmux kill-session -t "${session_name}"
  echo "Stopped session '${session_name}'."
}

parse_args "$@"

case "${ACTION}" in
  help|-h|--help)
    print_help
    ;;
  build)
    build_webui_export
    echo "Done."
    ;;
  start)
    ensure_engine_venv
    run_init_wizard_if_needed
    load_guarded_env
    if ((IS_DEV == 1)); then
      ensure_webui_deps
      start_session "sp-webui" "pnpm -C core/webui dev"
      start_session "sp-engine" "uv --project core/engine run core/engine/main.py --reload --reload-dir core/engine"
      echo "Done (dev mode)."
      echo "Use 'tmux attach -t sp-webui' or 'tmux attach -t sp-engine' to view logs."
      open_or_print_webui_url "dev"
    else
      ensure_webui_release_assets
      start_session "sp-engine" "uv --project core/engine run core/engine/main.py"
      echo "Done (production mode)."
      echo "WebUI is served by the engine. Use 'tmux attach -t sp-engine' to view logs."
      open_or_print_webui_url "prod"
    fi
    ;;
  stop)
    stop_session "sp-webui"
    stop_session "sp-engine"
    echo "Done."
    ;;
  *)
    print_help
    exit 1
    ;;
esac
