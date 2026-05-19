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

# Load internal profile written by install.sh (fallback for fresh installs)
# shellcheck source=/dev/null
[ -f "$HOME/.skillpilot/.profile" ] && source "$HOME/.skillpilot/.profile" || true
reload_shell_env

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_ENV_FILE="${ROOT_DIR}/config/.env"
ACTION="start"
ACTION_TARGET=""
TEST_FILES=()
DOCTOR_QUESTION=""
IS_DEV=0
NEXT_SERVER=0
SOURCE="manual"
AVAILABLE_PROVIDERS=()
LOADED_ENV_KEYS=()
HUMAN_DETECTION_REQUIREMENTS="${ROOT_DIR}/core/engine/mcp_servers/cameras/requirements-human-detection.txt"
LIVE_TTS_REQUIREMENTS="${ROOT_DIR}/core/engine/mcp_servers/live_tts/requirements-live-tts.txt"

print_help() {
  cat <<'EOF_HELP'
Usage: ./skillpilot.sh [help|build|start|stop|test|doctor] [--dev]
       ./skillpilot.sh <enable|disable> <human-detection|live-tts>
       ./skillpilot.sh doctor [question]
       ./skillpilot.sh test '[test_file[func1,func2]' | test_file:func1,func2 | test_file::func1 ...]

Commands:
  help    Show this help message.
  build   Build static webui export (core/webui/www).
  start   Start services. Default command.
  stop    Stop running tmux sessions. Use `--dev` to stop only development sessions.
  test    Run engine pytest suite, or only the named files under core/engine/tests.
  doctor  Open the configured doctor AI agent for troubleshooting and guided help.
  enable human-detection    Install optional human detection dependencies.
  disable human-detection   Uninstall optional human detection dependencies.
  enable live-tts           Install optional live-tts dependencies.
  disable live-tts          Uninstall optional live-tts dependencies.

Options:
  --dev   Use development mode for `start`, or stop only development sessions for `stop`.
  --next-server
          Production mode only. Serve the WebUI via `next start` (the Next.js production server)
          instead of the static HTML export served by the engine. Cannot be combined with `--dev`.
  --source <manual|webui>
          Identify the caller. `webui` restarts dev sessions and uses GUI auth for protected env reads when possible.

Defaults:
  - Command defaults to: start
  - Mode defaults to production (without --dev)
  - Test file names may omit ".py", may omit the "test_" prefix, and may be passed as space-separated or comma-separated values
  - Test selectors support file-scoped function filters: "media_mcp[text_to_image,text_to_song]"
  - zsh-safe alternatives are also supported: "media_mcp:text_to_image,text_to_song" or "media_mcp::text_to_image"
  - Empty brackets mean all tests in the file: "media_mcp[]"
  - Doctor questions may be passed inline: "./skillpilot.sh doctor why does install.sh fail on Linux?"
EOF_HELP
}

append_test_specs_from_arg() {
  local input="$1"
  local char current="" depth=0 i

  for ((i = 0; i < ${#input}; i++)); do
    char="${input:i:1}"
    case "${char}" in
      '[')
        depth=$((depth + 1))
        current+="${char}"
        ;;
      ']')
        if ((depth > 0)); then
          depth=$((depth - 1))
        fi
        current+="${char}"
        ;;
      ',')
        if ((depth == 0)); then
          current="${current#"${current%%[![:space:]]*}"}"
          current="${current%"${current##*[![:space:]]}"}"
          [[ -n "${current}" ]] && TEST_FILES+=("${current}")
          current=""
        else
          current+="${char}"
        fi
        ;;
      *)
        current+="${char}"
        ;;
    esac
  done

  current="${current#"${current%%[![:space:]]*}"}"
  current="${current%"${current##*[![:space:]]}"}"
  [[ -n "${current}" ]] && TEST_FILES+=("${current}")
}

parse_args() {
  local action_set=0
  local expect_test_files=0
  while (($# > 0)); do
    case "$1" in
      --source)
        shift
        if (($# == 0)); then
          echo "Error: --source requires a value."
          print_help
          exit 1
        fi
        SOURCE="$1"
        ;;
      --source=*)
        SOURCE="${1#*=}"
        ;;
      --dev)
        IS_DEV=1
        ;;
      --next-server)
        NEXT_SERVER=1
        ;;
      help|-h|--help|build|start|stop|test|doctor|enable|disable)
        if ((action_set == 1)); then
          echo "Error: multiple commands provided."
          print_help
          exit 1
        fi
        ACTION="$1"
        action_set=1
        if [[ "${ACTION}" == "test" ]]; then
          expect_test_files=1
        else
          expect_test_files=0
        fi
        ;;
      human-detection|live-tts)
        if [[ "${ACTION}" != "enable" && "${ACTION}" != "disable" ]]; then
          echo "Error: target '$1' requires enable/disable command."
          print_help
          exit 1
        fi
        if [[ -n "${ACTION_TARGET}" ]]; then
          echo "Error: multiple targets provided."
          print_help
          exit 1
        fi
        ACTION_TARGET="$1"
        ;;
      *)
        if ((expect_test_files == 1)); then
          append_test_specs_from_arg "$1"
          shift
          continue
        fi
        if [[ "${ACTION}" == "doctor" ]]; then
          if [[ -n "${DOCTOR_QUESTION}" ]]; then
            DOCTOR_QUESTION+=" "
          fi
          DOCTOR_QUESTION+="$1"
          shift
          continue
        fi
        echo "Error: unknown argument '$1'."
        print_help
        exit 1
        ;;
    esac
    shift
  done

  if ((IS_DEV == 1)) && [[ "${ACTION}" != "start" && "${ACTION}" != "stop" ]]; then
    echo "Error: --dev is only supported with 'start' or 'stop'."
    print_help
    exit 1
  fi

  if ((NEXT_SERVER == 1)) && [[ "${ACTION}" != "start" && "${ACTION}" != "stop" ]]; then
    echo "Error: --next-server is only supported with 'start' or 'stop'."
    print_help
    exit 1
  fi

  if ((NEXT_SERVER == 1)) && ((IS_DEV == 1)); then
    echo "Error: --next-server cannot be combined with --dev."
    print_help
    exit 1
  fi

  if [[ "${SOURCE}" != "manual" && "${SOURCE}" != "webui" ]]; then
    echo "Error: unsupported source '${SOURCE}'. Supported: manual, webui."
    print_help
    exit 1
  fi

  if [[ "${ACTION}" == "enable" || "${ACTION}" == "disable" ]]; then
    if [[ -z "${ACTION_TARGET}" ]]; then
      echo "Error: '${ACTION}' requires a target. Supported: human-detection, live-tts."
      print_help
      exit 1
    fi
    if [[ "${ACTION_TARGET}" != "human-detection" && "${ACTION_TARGET}" != "live-tts" ]]; then
      echo "Error: unsupported target '${ACTION_TARGET}'. Supported: human-detection, live-tts."
      print_help
      exit 1
    fi
  elif [[ -n "${ACTION_TARGET}" ]]; then
    echo "Error: target '${ACTION_TARGET}' is only valid with enable/disable."
    print_help
    exit 1
  fi
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Error: ${cmd} is required."
    exit 1
  fi
}

require_tmux() {
  if command -v tmux >/dev/null 2>&1; then
    return 0
  fi

  printf '\n\033[1m============================================================\033[0m\n'
  printf '\033[1m  Error: tmux is required but not found\033[0m\n'
  printf '\033[1m============================================================\033[0m\n\n'
  printf 'tmux is essential for Skill Pilot to run background\n'
  printf 'sessions and let you share the terminal with AI.\n\n'
  printf 'To fix this, re-run the installer:\n'
  printf '  bash install.sh\n\n'
  printf '  or\n\n'
  printf '  brew install tmux   # then re-run ./skillpilot.sh\n\n'
  printf 'Or raise an issue at:\n'
  printf '  https://github.com/x-school-academy/skill-pilot\n\n'
  exit 1
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
    echo "core/engine/.venv missing, running uv --directory core/engine sync..."
    if ! uv --directory "${ROOT_DIR}/core/engine" sync; then
      echo "Error: uv sync failed."
      echo "After installing dependencies, run:"
      echo "  uv --directory ${ROOT_DIR}/core/engine sync"
      exit 1
    fi
  fi
}

engine_venv_python() {
  local py="${ROOT_DIR}/core/engine/.venv/bin/python"
  ensure_engine_venv
  if [[ ! -x "${py}" ]]; then
    echo "Error: missing engine virtual environment at ${ROOT_DIR}/core/engine/.venv."
    echo "Run: uv --directory ${ROOT_DIR}/core/engine sync"
    exit 1
  fi
  echo "${py}"
}

install_human_detection_deps() {
  local py
  ensure_engine_venv
  py="$(engine_venv_python)"
  if [[ ! -f "${HUMAN_DETECTION_REQUIREMENTS}" ]]; then
    echo "Error: missing ${HUMAN_DETECTION_REQUIREMENTS}."
    exit 1
  fi
  echo "Installing optional human detection dependencies..."
  uv --directory "${ROOT_DIR}/core/engine" pip install --python "${py}" -r "${HUMAN_DETECTION_REQUIREMENTS}"
  echo "Human detection dependencies installed."
}

uninstall_human_detection_deps() {
  local py
  require_cmd uv
  py="$(engine_venv_python)"
  echo "Uninstalling optional human detection dependencies..."
  uv --directory "${ROOT_DIR}/core/engine" pip uninstall --python "${py}" ultralytics ultralytics-thop torch torchvision
  echo "Human detection dependencies removed."
}

install_live_tts_build_deps() {
  local os_name
  os_name="$(uname -s 2>/dev/null || true)"

  case "${os_name}" in
    Darwin)
      require_cmd brew
      echo "Installing macOS audio build dependencies (portaudio, pkg-config)..."
      brew install portaudio pkg-config
      ;;
    Linux)
      local use_sudo=0
      if [[ "$(id -u)" -ne 0 ]]; then
        require_cmd sudo
        use_sudo=1
      fi

      if command -v apt-get >/dev/null 2>&1; then
        echo "Installing Linux audio build dependencies (portaudio19-dev, pkg-config)..."
        if ((use_sudo == 1)); then
          sudo apt-get update
          sudo apt-get install -y portaudio19-dev pkg-config
        else
          apt-get update
          apt-get install -y portaudio19-dev pkg-config
        fi
      elif command -v dnf >/dev/null 2>&1; then
        echo "Installing Linux audio build dependencies (portaudio-devel, pkgconf-pkg-config)..."
        if ((use_sudo == 1)); then
          sudo dnf install -y portaudio-devel pkgconf-pkg-config
        else
          dnf install -y portaudio-devel pkgconf-pkg-config
        fi
      else
        echo "Error: unsupported Linux package manager."
        echo "Install PortAudio development headers manually, then retry."
        exit 1
      fi
      ;;
    *)
      echo "Error: live-tts enable is supported on macOS and Linux only."
      exit 1
      ;;
  esac
}

install_live_tts_deps() {
  local py
  ensure_engine_venv
  py="$(engine_venv_python)"
  if [[ ! -f "${LIVE_TTS_REQUIREMENTS}" ]]; then
    echo "Error: missing ${LIVE_TTS_REQUIREMENTS}."
    exit 1
  fi
  install_live_tts_build_deps
  echo "Installing optional live-tts dependencies..."
  uv --directory "${ROOT_DIR}/core/engine" pip install --python "${py}" -r "${LIVE_TTS_REQUIREMENTS}"
  echo "Live-tts dependencies installed."
}

uninstall_live_tts_deps() {
  local py
  require_cmd uv
  py="$(engine_venv_python)"
  echo "Uninstalling optional live-tts dependencies..."
  uv --directory "${ROOT_DIR}/core/engine" pip uninstall --python "${py}" pyaudio
  echo "Live-tts dependencies removed."
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

press_any_key() {
  local msg="${1:-Press any key to continue, or Ctrl-C to exit.}"
  printf '\033[1m%s\033[0m ' "$msg"
  local input_fd="/dev/tty"
  { true </dev/tty; } 2>/dev/null || input_fd="/dev/stdin"
  read -r -s -n 1 <"$input_fd" || true
  printf '\n'
}

show_screen() {
  printf '\n\033[1m============================================================\033[0m\n'
  printf '\033[1m  %s\033[0m\n' "$1"
  printf '\033[1m============================================================\033[0m\n\n'
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
      echo "Invalid port '${chosen}'. Enter a number between 1 and 65535." >&2
      continue
    fi

    if [[ -n "${blocked_port}" && "${chosen}" == "${blocked_port}" ]]; then
      echo "Port ${chosen} is already used by another Skill Pilot service." >&2
      continue
    fi

    if port_available "${host}" "${chosen}"; then
      echo "${chosen}"
      return
    fi

    echo "Port ${chosen} is not available on ${host}." >&2
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

extract_default_provider_value() {
  local key="$1"
  local config_path="${ROOT_DIR}/config/ai_providers.json5"

  if [[ ! -f "${config_path}" ]]; then
    return
  fi

  sed -n "/default[[:space:]]*:[[:space:]]*{/,/}/{s/.*${key}[[:space:]]*:[[:space:]]*'\\([^']*\\)'.*/\\1/p; s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p;}" "${config_path}" | head -n 1
}

doctor_default_provider() {
  local provider_id=""
  provider_id="$(extract_default_provider_value "doctor")"
  if [[ -z "${provider_id}" ]]; then
    provider_id="$(extract_default_provider_value "llm")"
  fi
  if [[ -z "${provider_id}" ]]; then
    provider_id="opencode"
  fi
  echo "${provider_id}"
}

doctor_provider_block() {
  local provider_id="$1"
  local config_path="${ROOT_DIR}/config/ai_providers.json5"

  awk -v provider="${provider_id}" '
    BEGIN { capture = 0 }
    {
      if (capture == 0) {
        if ($0 ~ ("id[[:space:]]*:[[:space:]]*'\''" provider "'\''") || $0 ~ ("\"id\"[[:space:]]*:[[:space:]]*\"" provider "\"")) {
          capture = 1
        }
        next
      }

      if ($0 ~ /^[[:space:]][[:space:]][[:space:]][[:space:]]\}[,]?[[:space:]]*$/) {
        exit
      }

      print
    }
  ' "${config_path}"
}

doctor_provider_field() {
  local provider_id="$1"
  local field_name="$2"
  local block=""

  block="$(doctor_provider_block "${provider_id}")"
  if [[ -z "${block}" ]]; then
    return
  fi

  printf '%s\n' "${block}" | sed -n "s/.*${field_name}[[:space:]]*:[[:space:]]*'\\([^']*\\)'.*/\\1/p; s/.*\"${field_name}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" | head -n 1
}

doctor_provider_terminal_args_line() {
  local provider_id="$1"
  local block=""

  block="$(doctor_provider_block "${provider_id}")"
  if [[ -z "${block}" ]]; then
    return
  fi

  printf '%s\n' "${block}" | sed -n "s/.*terminal-args[[:space:]]*:[[:space:]]*\\(\\[[^]]*\\]\\).*/\\1/p; s/.*\"terminal-args\"[[:space:]]*:[[:space:]]*\\(\\[[^]]*\\]\\).*/\\1/p; s/.*'terminal-args'[[:space:]]*:[[:space:]]*\\(\\[[^]]*\\]\\).*/\\1/p" | head -n 1
}

doctor_append_args_from_line() {
  local raw="$1"
  local prompt="$2"
  local rest="${raw}"
  local token=""

  while [[ "${rest}" =~ \'([^\']*)\' ]]; do
    token="${BASH_REMATCH[1]}"
    if [[ "${token}" == "{{prompt}}" ]]; then
      DOCTOR_CMD+=("${prompt}")
    else
      DOCTOR_CMD+=("${token}")
    fi
    rest="${rest#*"'"${token}"'"}"
  done

  if ((${#DOCTOR_CMD[@]} > 1)); then
    return
  fi

  rest="${raw}"
  while [[ "${rest}" =~ \"([^\"]*)\" ]]; do
    token="${BASH_REMATCH[1]}"
    if [[ "${token}" == "{{prompt}}" ]]; then
      DOCTOR_CMD+=("${prompt}")
    else
      DOCTOR_CMD+=("${token}")
    fi
    rest="${rest#*"\"${token}\""}"
  done
}

doctor_build_command() {
  local provider_id="$1"
  local prompt="$2"
  local bin_name=""
  local terminal_args_line=""
  local model_name=""

  DOCTOR_CMD=()
  bin_name="$(doctor_provider_field "${provider_id}" "bin")"
  if [[ -z "${bin_name}" ]]; then
    return 1
  fi

  DOCTOR_CMD=("${bin_name}")
  if [[ "${provider_id}" != "opencode" ]]; then
    model_name="$(doctor_provider_field "${provider_id}" "model")"
    if [[ -n "${model_name}" ]]; then
      DOCTOR_CMD+=("--model" "${model_name}")
    fi
  fi

  terminal_args_line="$(doctor_provider_terminal_args_line "${provider_id}")"
  if [[ -n "${terminal_args_line}" ]]; then
    doctor_append_args_from_line "${terminal_args_line}" "${prompt}"
  else
    DOCTOR_CMD+=("${prompt}")
  fi

  if ((${#DOCTOR_CMD[@]} == 0)); then
    return 1
  fi
  return 0
}

ensure_opencode_installed() {
  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  echo "OpenCode is not installed. Trying to install it now..."

  if command -v pnpm >/dev/null 2>&1; then
    echo "Trying: pnpm install -g opencode-ai"
    if pnpm install -g opencode-ai; then
      reload_shell_env
    fi
  fi
  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  if command -v curl >/dev/null 2>&1; then
    echo "Trying: curl -fsSL https://opencode.ai/install | bash"
    if curl -fsSL https://opencode.ai/install | bash; then
      reload_shell_env
    fi
  fi
  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  if command -v brew >/dev/null 2>&1; then
    echo "Trying: brew install anomalyco/tap/opencode"
    if brew install anomalyco/tap/opencode; then
      reload_shell_env
    fi
  fi
  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  if command -v bun >/dev/null 2>&1; then
    echo "Trying: bun add -g opencode-ai"
    if bun add -g opencode-ai; then
      reload_shell_env
    fi
  fi
  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  if command -v paru >/dev/null 2>&1; then
    echo "Trying: paru -S opencode"
    if paru -S opencode; then
      reload_shell_env
    fi
  fi

  if command -v opencode >/dev/null 2>&1; then
    return 0
  fi

  echo "Error: failed to install opencode automatically."
  echo "Please install it manually with one of these commands:"
  echo "  pnpm install -g opencode-ai"
  echo "  curl -fsSL https://opencode.ai/install | bash"
  echo "  brew install anomalyco/tap/opencode"
  echo "  bun add -g opencode-ai"
  echo "  paru -S opencode"
  return 1
}

resolve_doctor_question() {
  local input_fd="/dev/tty"
  local output_fd="/dev/tty"
  local first_line=""
  local line=""

  if [[ -n "${DOCTOR_QUESTION}" ]]; then
    echo "${DOCTOR_QUESTION}"
    return
  fi

  { true </dev/tty; } 2>/dev/null || {
    input_fd="/dev/stdin"
    output_fd="/dev/stderr"
  }
  printf '%s\n' "Please describe any problem I can help you, for example:" >"${output_fd}"
  printf '%s\n' "  install.sh failed while installing a dependency" >"${output_fd}"
  printf '%s\n' "  skillpilot.sh start does not open the WebUI" >"${output_fd}"
  printf '%s\n' "  I do not understand a technical term or error message" >"${output_fd}"
  printf '%s\n' "  Skill Pilot code has a bug and I want help fixing it" >"${output_fd}"
  printf '%s\n' 'Use """ to begin a multi-line message, and end with """' >"${output_fd}"
  printf '%s' "Question: " >"${output_fd}"

  read -r first_line <"${input_fd}" || true
  if [[ "${first_line}" == '"""' ]]; then
    DOCTOR_QUESTION=""
    while true; do
      read -r line <"${input_fd}" || break
      if [[ "${line}" == '"""' ]]; then
        break
      fi
      if [[ -n "${DOCTOR_QUESTION}" ]]; then
        DOCTOR_QUESTION+=$'\n'
      fi
      DOCTOR_QUESTION+="${line}"
    done
  else
    DOCTOR_QUESTION="${first_line}"
  fi

  echo "${DOCTOR_QUESTION}"
}

doctor_prompt_text() {
  local question="$1"
  cat <<EOF_DOCTOR
You are helping a zero-knowledge Skill Pilot user.

The user may have problems with install.sh or skillpilot.sh because each system is different, they may not understand technical terms, or the code may have bugs. Help with troubleshooting, plain-language explanations, commands to run, finding errors, and fixing Skill Pilot code when needed.

Use the skill-pilot-doctor skill when needed.

User question:
${question}
EOF_DOCTOR
}

run_doctor() {
  local question=""
  local provider_id=""
  local selected_provider=""
  local prompt_text=""
  local provider_bin=""

  question="$(resolve_doctor_question)"
  question="${question#"${question%%[![:space:]]*}"}"
  question="${question%"${question##*[![:space:]]}"}"
  if [[ -z "${question}" ]]; then
    echo "Error: doctor requires a question."
    exit 1
  fi

  provider_id="$(doctor_default_provider)"
  selected_provider="${provider_id}"

  if ! doctor_build_command "${selected_provider}" "test"; then
    selected_provider="opencode"
  fi

  provider_bin="$(doctor_provider_field "${selected_provider}" "bin")"
  if [[ -z "${provider_bin}" ]]; then
    selected_provider="opencode"
    provider_bin="opencode"
  fi

  if ! command -v "${provider_bin}" >/dev/null 2>&1; then
    if [[ "${selected_provider}" != "opencode" ]]; then
      echo "Configured doctor provider '${selected_provider}' is not installed. Falling back to opencode."
      selected_provider="opencode"
    fi
    ensure_opencode_installed
  fi

  prompt_text="$(doctor_prompt_text "${question}")"
  if ! doctor_build_command "${selected_provider}" "${prompt_text}"; then
    echo "Error: failed to build the doctor command for provider '${selected_provider}'."
    exit 1
  fi

  if [[ "${selected_provider}" == "opencode" ]]; then
    echo "I will send your question to opencode AI agent to help you resolve the problem, you can chat with it just as chatbot, but it can almost do any for you, troubleshooting, run command, find errors, even fix skill pilot code, once finished you can exit by slash command /exit or double ctrl-c"
  else
    echo "I will send your question to the '${selected_provider}' doctor agent. You can continue chatting in the agent session and exit when you are done."
  fi
  echo ""
  press_any_key "Press Enter to continue."
  "${DOCTOR_CMD[@]}"
}

update_settings_json5() {
  local host="$1"
  local prod_engine_port="$2"
  local dev_engine_port="$3"
  local dev_webui_port="$4"
  local py
  py="$(engine_python)"

  "${py}" - "${ROOT_DIR}/config/settings.json5" "${host}" "${prod_engine_port}" "${dev_engine_port}" "${dev_webui_port}" <<'PY'
import json
import sys
from pathlib import Path

import json5

settings_path = Path(sys.argv[1])
host = sys.argv[2]
prod_engine_port = int(sys.argv[3])
dev_engine_port = int(sys.argv[4])
dev_webui_port = int(sys.argv[5])

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
webui_dev = webui.setdefault("development", {})
if not isinstance(webui_dev, dict):
    webui_dev = {}
    webui["development"] = webui_dev
webui_dev["port"] = dev_webui_port

engine = services.setdefault("engine", {})
if not isinstance(engine, dict):
    engine = {}
    services["engine"] = engine
engine["host"] = host
engine_prod = engine.setdefault("production", {})
if not isinstance(engine_prod, dict):
    engine_prod = {}
    engine["production"] = engine_prod
engine_prod["port"] = prod_engine_port
engine_dev = engine.setdefault("development", {})
if not isinstance(engine_dev, dict):
    engine_dev = {}
    engine["development"] = engine_dev
engine_dev["port"] = dev_engine_port

settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

update_ai_providers_json5() {
  local provider_id="$1"
  shift
  local installed_providers=("$@")
  local py
  py="$(engine_python)"

  "${py}" - "${ROOT_DIR}/config/ai_providers.json5" "${provider_id}" "${installed_providers[@]}" <<'PY'
import json
import sys
from pathlib import Path

import json5

providers_path = Path(sys.argv[1])
default_provider = sys.argv[2]
installed_providers = set(sys.argv[3:])

data = json5.loads(providers_path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit("Invalid ai_providers.json5 format")

defaults = data.setdefault("default", {})
if not isinstance(defaults, dict):
    defaults = {}
    data["default"] = defaults
defaults["llm"] = default_provider
defaults["doctor"] = default_provider

llm = data.get("llm", [])
if isinstance(llm, list):
    for item in llm:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        # disabled=False for any installed provider, disabled=True for missing ones
        item["disabled"] = item_id not in installed_providers

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
  if command -v copilot >/dev/null 2>&1; then
    AVAILABLE_PROVIDERS+=("copilot")
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

kill_all_sp_sessions() {
  local sessions=("sp-engine-prod" "sp-engine-dev" "sp-webui-dev")
  local killed=0
  for s in "${sessions[@]}"; do
    if tmux has-session -t "${s}" 2>/dev/null; then
      tmux kill-session -t "${s}"
      echo "Stopped existing tmux session '${s}'."
      killed=1
    fi
  done
  if ((killed)); then
    echo "Cleared old sessions to free ports for this installation."
    echo ""
  fi
}

run_init_wizard_if_needed() {
  local workspace_config="${ROOT_DIR}/workspace/config/ai_providers.json5"
  if [[ ! -f "${workspace_config}" ]]; then
    echo "workspace/config/ai_providers.json5 not found — initialising workspace submodule..."
    git -C "${ROOT_DIR}" submodule update --init --recursive workspace
  fi

  if [[ -f "${ENGINE_ENV_FILE}" || -L "${ENGINE_ENV_FILE}" ]]; then
    return
  fi

  # Kill any leftover sessions from a previous install in a different directory
  # to avoid port conflicts on first-time setup.
  if command -v tmux >/dev/null 2>&1; then
    kill_all_sp_sessions
  fi

  # Wizard Screen 2 — Intro
  show_screen "Skill Pilot First-Time Setup"
  echo "Welcome! This wizard will walk you through a few settings"
  echo "before Skill Pilot starts for the first time."
  echo ""
  echo "Each step includes a short explanation of what you are"
  echo "choosing and why it matters."
  press_any_key "Press any key to begin."

  local listen_host only_allow_https
  local prod_engine_port dev_engine_port dev_webui_port
  local provider_id=""
  local webui_auth_token

  # Wizard Screen 3 — Ports and addresses education
  show_screen "Understanding Ports and Addresses"
  echo 'When your computer runs a web service, it listens on a'
  echo '"port" — a numbered door where connections arrive.'
  echo ""
  echo "Think of your computer as a building:"
  echo "  IP address = the building address"
  echo "  Port number = the specific room inside the building"
  echo ""
  echo "Common port numbers you will use with Skill Pilot:"
  echo ""
  echo "  3001  ->  Production engine API and bundled release UI"
  echo "  3002  ->  Development engine API"
  echo "  3003  ->  Development WebUI"
  echo ""
  echo "What is 127.0.0.1?"
  echo '  This is called "localhost" — it means your own computer.'
  echo "  When you open http://127.0.0.1:3003 in a browser, you"
  echo "  are connecting to a service running on your own machine."
  echo "  No one else on the internet can access it."
  echo ""
  echo "What is 0.0.0.0?"
  echo '  This means "listen on all network interfaces" — your'
  echo "  computer will accept connections from other devices on"
  echo "  your local network (like your phone or another laptop)."
  press_any_key "Press any key to choose your network binding."

  # Wizard Screen 4 — Choose host binding
  show_screen "Choose Where Skill Pilot Listens"
  echo "  1)  127.0.0.1  (localhost — your computer only)"
  echo "      Safest option. Only you can access Skill Pilot."
  echo "      Best for: personal use on a single machine."
  echo ""
  echo "  2)  0.0.0.0    (all interfaces — local network access)"
  echo "      Other devices on your home or office network can"
  echo "      also connect to Skill Pilot."
  echo "      Best for: accessing from your phone or tablet."
  echo ""
  local host_choice
  while true; do
    read -r -p "Enter your choice [1/2]: " host_choice
    case "${host_choice:-1}" in
      1) listen_host="127.0.0.1"; break ;;
      2) listen_host="0.0.0.0";   break ;;
      *) echo "Please enter 1 or 2." ;;
    esac
  done
  only_allow_https=0
  if [[ "${listen_host}" != "127.0.0.1" && "${listen_host}" != "localhost" ]]; then
    # Wizard Screen 4b — HTTPS explanation
    show_screen "HTTP vs HTTPS"
    echo "When a service is accessible on your local network (not"
    echo "just localhost), it is good practice to encrypt the"
    echo "connection."
    echo ""
    echo "  HTTP   = plain text — data can be read if intercepted"
    echo "  HTTPS  = encrypted — safe even on shared networks"
    echo ""
    echo "Do you plan to access Skill Pilot only within your local"
    echo "home or office network?"
    echo ""
    echo "  1)  Yes — local network only (ONLY_ALLOW_HTTPS=0)"
    echo "      HTTP is acceptable. Simpler setup."
    echo ""
    echo "  2)  No — I may expose it to the public internet (ONLY_ALLOW_HTTPS=1)"
    echo "      HTTPS will be enforced for safety."
    echo ""
    echo "Note: You can change this later by editing:"
    echo "  config/.env  ->  ONLY_ALLOW_HTTPS=0  or  1"
    echo ""
    local https_choice
    while true; do
      read -r -p "Enter your choice [1/2]: " https_choice
      case "${https_choice:-1}" in
        1) only_allow_https=0; break ;;
        2) only_allow_https=1; break ;;
        *) echo "Please enter 1 or 2." ;;
      esac
    done
  fi

  # Wizard Screen 4c — Choose ports
  show_screen "Choose Your Port Numbers"
  echo "Skill Pilot can run production and development side by side."
  echo ""
  echo "Choose default ports for these services:"
  echo ""
  echo "  Prod engine  ->  Release engine API and bundled release UI"
  echo "  Dev engine   ->  Reloading engine API for development"
  echo "  Dev WebUI    ->  Next.js development server"
  echo ""
  echo "The defaults work for most setups. Change them only if"
  echo "another program on your computer is already using that port."
  echo ""
  echo "Press Enter to accept the default, or type a port number (1-65535)."
  echo ""
  prod_engine_port="$(pick_port "Prod (Engine API)" "${listen_host}" "3001")"
  dev_engine_port="$(pick_port "Dev  (Engine API)" "${listen_host}" "3002" "${prod_engine_port}")"
  dev_webui_port="$(pick_port "Dev  (WebUI)" "${listen_host}" "3003" "${prod_engine_port}")"
  while [[ "${dev_webui_port}" == "${dev_engine_port}" ]]; do
    echo "Port ${dev_webui_port} is already used by another Skill Pilot service." >&2
    dev_webui_port="$(pick_port "Dev  (WebUI)" "${listen_host}" "3003" "${prod_engine_port}")"
  done
  echo ""
  echo "  Prod engine: ${prod_engine_port}  ->  http://${listen_host}:${prod_engine_port}"
  echo "  Dev  engine: ${dev_engine_port}  ->  http://${listen_host}:${dev_engine_port}"
  echo "  Dev  WebUI : ${dev_webui_port}  ->  http://${listen_host}:${dev_webui_port}"
  press_any_key

  # Wizard Screen 5 — AI agent CLI detection
  show_screen "AI Agent CLI Tools"
  echo "Skill Pilot works with these AI code agent CLIs:"
  echo ""
  echo "  claude    Claude Code by Anthropic"
  echo "  copilot   GitHub Copilot CLI"
  echo "  codex     OpenAI Codex CLI"
  echo "  gemini    Google Gemini CLI"
  echo "  opencode  OpenCode (open source, OpenAI-compatible)"
  echo ""
  echo "Checking what you have installed..."
  echo ""
  detect_available_providers
  local all_agents=("claude" "copilot" "codex" "gemini" "opencode")
  for agent in "${all_agents[@]}"; do
    local found=0
    for p in "${AVAILABLE_PROVIDERS[@]}"; do
      [[ "$p" == "$agent" ]] && found=1 && break
    done
    if ((found)); then
      printf '  \033[0;32m%-10s  ✓ installed\033[0m\n' "${agent}"
    else
      printf '  \033[1;33m%-10s  ✗ not found\033[0m\n' "${agent}"
    fi
  done
  echo ""

  if ((${#AVAILABLE_PROVIDERS[@]} == 0)); then
    echo "Error: no AI agent CLI is available."
    echo "Run 'bash install.sh' to install supported AI code agents, then re-run ./skillpilot.sh."
    exit 1
  fi

  # Wizard Screen 6 — Choose default provider
  if ((${#AVAILABLE_PROVIDERS[@]} == 1)); then
    provider_id="${AVAILABLE_PROVIDERS[0]}"
    echo "Using ${provider_id} as the default AI agent."
  else
    show_screen "Choose Your Default AI Agent"
    echo "Which AI agent do you want Skill Pilot to use by default?"
    echo "You can change this later in config/ai_providers.json5."
    echo ""
    local i=1
    for p in "${AVAILABLE_PROVIDERS[@]}"; do
      echo "  ${i})  ${p}"
      ((i++))
    done
    echo ""
    local provider_choice
    while true; do
      read -r -p "Enter your choice [1]: " provider_choice
      provider_choice="${provider_choice:-1}"
      if [[ "${provider_choice}" =~ ^[0-9]+$ ]] && \
         ((provider_choice >= 1 && provider_choice <= ${#AVAILABLE_PROVIDERS[@]})); then
        provider_id="${AVAILABLE_PROVIDERS[$((provider_choice - 1))]}"
        echo "Default AI agent: ${provider_id}"
        break
      fi
      echo "Invalid selection. Enter a number from 1 to ${#AVAILABLE_PROVIDERS[@]}."
    done
  fi

  # Auto-generate auth token (no prompt needed for beginners)
  webui_auth_token="$(generate_uuid)"

  write_engine_env "${only_allow_https}" "${webui_auth_token}" "none" "" ""
  update_settings_json5 "${listen_host}" "${prod_engine_port}" "${dev_engine_port}" "${dev_webui_port}"
  update_ai_providers_json5 "${provider_id}" "${AVAILABLE_PROVIDERS[@]}"

  # Wizard Screen 7 — Configuration saved
  show_screen "Configuration Saved"
  echo "Your settings have been written to:"
  echo "  config/.env"
  echo "  config/settings.json5"
  echo "  config/ai_providers.json5"
  echo ""
  echo "You can review and edit these files at any time."
  press_any_key "Press any key to start Skill Pilot."
}

get_service_port() {
  local service_name="$1"
  local mode="$2"
  local py
  py="$(engine_python)"
  "${py}" - "${ROOT_DIR}/config/settings.json5" "${service_name}" "${mode}" "port" <<'PY'
import sys
from pathlib import Path

try:
    import json5
except Exception:
    json5 = None

settings_path = Path(sys.argv[1])
service_name = sys.argv[2]
mode = sys.argv[3]
field_name = sys.argv[4]

default_ports = {
    ("engine", "production"): 3001,
    ("engine", "development"): 3002,
    ("webui", "development"): 3003,
}

default_port = default_ports.get((service_name, mode), 3001)
default_host = "127.0.0.1"

try:
    data = json5.loads(settings_path.read_text(encoding="utf-8")) if json5 else {}
except Exception:
    data = {}

services = data.get("services", {}) if isinstance(data, dict) else {}
service = services.get(service_name, {}) if isinstance(services, dict) else {}
mode_config = service.get(mode, {}) if isinstance(service, dict) else {}

if not isinstance(service, dict):
    service = {}
if not isinstance(mode_config, dict):
    mode_config = {}

if field_name == "host":
    value = mode_config.get(field_name, service.get(field_name, default_host))
else:
    value = mode_config.get(field_name, default_port)
if field_name == "port":
    print(int(value))
else:
    print(str(value))
PY
}

get_service_host() {
  local service_name="$1"
  local mode="$2"
  local py
  py="$(engine_python)"
  "${py}" - "${ROOT_DIR}/config/settings.json5" "${service_name}" "${mode}" "host" <<'PY'
import sys
from pathlib import Path

try:
    import json5
except Exception:
    json5 = None

settings_path = Path(sys.argv[1])
service_name = sys.argv[2]
mode = sys.argv[3]
field_name = sys.argv[4]

default_ports = {
    ("engine", "production"): 3001,
    ("engine", "development"): 3002,
    ("webui", "development"): 3003,
}

default_port = default_ports.get((service_name, mode), 3001)
default_host = "127.0.0.1"

try:
    data = json5.loads(settings_path.read_text(encoding="utf-8")) if json5 else {}
except Exception:
    data = {}

services = data.get("services", {}) if isinstance(data, dict) else {}
service = services.get(service_name, {}) if isinstance(services, dict) else {}
mode_config = service.get(mode, {}) if isinstance(service, dict) else {}

if not isinstance(service, dict):
    service = {}
if not isinstance(mode_config, dict):
    mode_config = {}

if field_name == "host":
    value = mode_config.get(field_name, service.get(field_name, default_host))
else:
    value = mode_config.get(field_name, default_port)
print(str(value))
PY
}

get_service_base_url() {
  local service_name="$1"
  local mode="$2"
  local host port
  host="$(get_service_host "${service_name}" "${mode}")"
  port="$(get_service_port "${service_name}" "${mode}")"
  echo "http://${host}:${port}/"
}

build_webui_export() {
  ensure_webui_deps
  rm -f \
    "${ROOT_DIR}/core/webui/.next/lock" \
    "${ROOT_DIR}/core/webui/.next/dev/lock" \
    "${ROOT_DIR}/core/webui/www/lock"
  echo "Building static webui export..."
  pnpm -C "${ROOT_DIR}/core/webui" export
}

run_engine_tests() {
  require_cmd uv

  local tests_dir="${ROOT_DIR}/core/engine/tests"
  local pytest_targets=()
  local spec name path func_spec raw_func normalized_func added_func_target
  local -a funcs

  if [[ ! -d "${tests_dir}" ]]; then
    echo "Error: missing tests directory at ${tests_dir}."
    exit 1
  fi

  if ((${#TEST_FILES[@]} == 0)); then
    pytest_targets=("tests")
  else
    for spec in "${TEST_FILES[@]}"; do
      name="${spec}"
      func_spec=""
      if [[ "${spec}" == *'['* ]]; then
        if [[ "${spec}" != *']' ]] || [[ "${spec}" == \[* ]] || [[ "${spec}" == *']'*'['* ]]; then
          echo "Error: invalid test selector '${spec}'. Expected file[func1,func2]."
          exit 1
        fi
        name="${spec%%[*}"
        func_spec="${spec#*[}"
        func_spec="${func_spec%]}"
        if [[ -z "${name}" ]]; then
          echo "Error: invalid test selector '${spec}'. Expected file[func1,func2]."
          exit 1
        fi
      elif [[ "${spec}" == *"::"* ]]; then
        name="${spec%%::*}"
        func_spec="${spec#*::}"
      elif [[ "${spec}" == *":"* ]]; then
        name="${spec%%:*}"
        func_spec="${spec#*:}"
      fi
      if [[ "${name}" == */* ]]; then
        echo "Error: test files must be file names only under core/engine/tests: '${name}'."
        exit 1
      fi
      [[ "${name}" == test_* ]] || name="test_${name}"
      [[ "${name}" == *.py ]] || name="${name}.py"
      path="${tests_dir}/${name}"
      if [[ ! -f "${path}" ]]; then
        echo "Error: test file not found: ${path}"
        exit 1
      fi
      if [[ -z "${func_spec}" ]]; then
        pytest_targets+=("tests/${name}")
        continue
      fi

      funcs=()
      if [[ -n "${func_spec}" ]]; then
        IFS=',' read -r -a funcs <<< "${func_spec}"
      fi
      if ((${#funcs[@]} == 0)); then
        pytest_targets+=("tests/${name}")
        continue
      fi

      added_func_target=0
      for raw_func in "${funcs[@]}"; do
        raw_func="${raw_func#"${raw_func%%[![:space:]]*}"}"
        raw_func="${raw_func%"${raw_func##*[![:space:]]}"}"
        [[ -n "${raw_func}" ]] || continue
        normalized_func="${raw_func}"
        [[ "${normalized_func}" == test_* ]] || normalized_func="test_${normalized_func}"
        pytest_targets+=("tests/${name}::${normalized_func}")
        added_func_target=1
      done

      if ((added_func_target == 0)); then
        pytest_targets+=("tests/${name}")
      fi
    done
  fi

  echo "Running engine tests: ${pytest_targets[*]}"
  uv --directory "${ROOT_DIR}/core/engine" run pytest -s "${pytest_targets[@]}"
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

  unset SAFE_DOTENV_LOADED_KEYS

  local env_content=""
  if [[ -r "${ENGINE_ENV_FILE}" ]]; then
    env_content="$(cat "${ENGINE_ENV_FILE}")"
  else
    echo "Loading protected env from ${ENGINE_ENV_FILE} (sudo required)..."
    if [[ "${SOURCE}" == "webui" ]] && has_gui_env; then
      env_content="$(read_protected_file_with_gui "${ENGINE_ENV_FILE}")"
    else
      sudo -k
      env_content="$(sudo cat -- "${ENGINE_ENV_FILE}")"
      sudo -k
    fi
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

  if ((${#loaded_keys[@]} > 0)); then
    local loaded_key_csv
    loaded_key_csv="$(IFS=,; echo "${loaded_keys[*]}")"
    export SAFE_DOTENV_LOADED_KEYS="${loaded_key_csv}"
    LOADED_ENV_KEYS=("${loaded_keys[@]}")
  fi

  export IN_KEYS_SAFE_GUARD=1
  export SKILL_PILOT_ENV_ALREADY_LOADED=1
}

sync_tmux_environment() {
  if ((${#LOADED_ENV_KEYS[@]} == 0)); then
    return
  fi

  if ! tmux info >/dev/null 2>&1; then
    return
  fi

  local existing_key
  local existing_loaded_keys
  local key
  local -a existing_keys=()
  local sync_keys=("${LOADED_ENV_KEYS[@]}" "SAFE_DOTENV_LOADED_KEYS" "IN_KEYS_SAFE_GUARD" "SKILL_PILOT_ENV_ALREADY_LOADED")

  existing_loaded_keys="$(tmux show-environment -g SAFE_DOTENV_LOADED_KEYS 2>/dev/null || true)"
  existing_loaded_keys="${existing_loaded_keys#SAFE_DOTENV_LOADED_KEYS=}"
  if [[ -n "${existing_loaded_keys}" && "${existing_loaded_keys}" != -* ]]; then
    IFS=',' read -r -a existing_keys <<< "${existing_loaded_keys}"
    for existing_key in "${existing_keys[@]}"; do
      [[ -n "${existing_key}" ]] || continue
      if [[ ",${SAFE_DOTENV_LOADED_KEYS}," != *",${existing_key},"* ]]; then
        tmux set-environment -gu "${existing_key}" >/dev/null 2>&1 || true
      fi
    done
  fi

  for key in "${sync_keys[@]}"; do
    [[ -n "${key}" ]] || continue
    if [[ "${!key+x}" == "x" ]]; then
      tmux set-environment -g "${key}" "${!key}" >/dev/null
    fi
  done
}


get_webui_base_url() {
  local mode="$1"
  if [[ "${mode}" == "dev" ]]; then
    get_service_base_url "webui" "development"
  elif ((NEXT_SERVER == 1)); then
    get_service_base_url "webui" "development"
  else
    get_service_base_url "engine" "production"
  fi
}

_sp_has_interactive_tty() {
  [[ -t 0 && -t 1 && -t 2 ]]
}

_sp_is_ssh() {
  [[ -n "${SSH_CONNECTION-}" || -n "${SSH_TTY-}" ]]
}

_sp_has_linux_gui() {
  if [[ -n "${DISPLAY-}" || -n "${WAYLAND_DISPLAY-}" ]]; then
    return 0
  fi
  if command -v loginctl >/dev/null 2>&1 && [[ -n "${XDG_SESSION_ID-}" ]]; then
    local session_type
    session_type="$(loginctl show-session "${XDG_SESSION_ID}" -p Type --value 2>/dev/null || true)"
    [[ "${session_type}" == "x11" || "${session_type}" == "wayland" ]] && return 0
  fi
  return 1
}

_sp_has_macos_gui() {
  local console_user
  console_user="$(/usr/bin/stat -f%Su /dev/console 2>/dev/null || true)"
  [[ -n "${console_user}" && "${console_user}" != "root" && "${console_user}" != "loginwindow" ]] && ! _sp_is_ssh
}

has_gui_env() {
  local os_type
  os_type="$(uname -s 2>/dev/null || true)"
  if [[ "${os_type}" == "Darwin" ]]; then
    _sp_has_macos_gui
  else
    _sp_has_linux_gui && ! _sp_is_ssh
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

read_protected_file_with_gui() {
  local file_path="$1"
  local os_type rc tmp_script
  os_type="$(uname -s 2>/dev/null || true)"

  if ! has_gui_env; then
    echo "Error: GUI auth requested but no GUI session detected (SSH session or no display)." >&2
    return 1
  fi

  tmp_script="$(mktemp /tmp/skillpilot-read-env.XXXXXX.sh)"
  cat > "${tmp_script}" <<'SCRIPT'
#!/bin/bash
set -euo pipefail
cat -- "$1"
SCRIPT
  chmod +x "${tmp_script}"

  if [[ "${os_type}" == "Darwin" ]]; then
    local cmd esc
    cmd="bash $(printf '%q' "${tmp_script}") $(printf '%q' "${file_path}")"
    esc="${cmd//\\/\\\\}"
    esc="${esc//\"/\\\"}"
    if /usr/bin/osascript -e "do shell script \"${esc}\" with administrator privileges" 2>/dev/null; then
      rm -f "${tmp_script}"
      return 0
    fi
    rm -f "${tmp_script}"
    echo "Error: macOS GUI auth dialog failed or was cancelled." >&2
    return 1
  fi

  if command -v pkexec >/dev/null 2>&1; then
    if pkexec bash "${tmp_script}" "${file_path}"; then
      rm -f "${tmp_script}"
      return 0
    fi
    rc=$?
    echo "Warning: pkexec failed (exit ${rc}); trying askpass fallback." >&2
  fi

  local askpass_tmp=""
  if command -v zenity >/dev/null 2>&1; then
    askpass_tmp="$(mktemp /tmp/askpass.XXXXXX.sh)"
    printf '#!/bin/sh\nexec zenity --password --title="sudo password"\n' > "${askpass_tmp}"
    chmod +x "${askpass_tmp}"
  elif command -v kdialog >/dev/null 2>&1; then
    askpass_tmp="$(mktemp /tmp/askpass.XXXXXX.sh)"
    printf '#!/bin/sh\nexec kdialog --password "sudo password"\n' > "${askpass_tmp}"
    chmod +x "${askpass_tmp}"
  fi

  if [[ -n "${askpass_tmp}" ]]; then
    sudo -k
    if SUDO_ASKPASS="${askpass_tmp}" sudo -A bash "${tmp_script}" "${file_path}"; then
      rc=0
    else
      rc=$?
    fi
    rm -f "${askpass_tmp}" "${tmp_script}"
    return ${rc}
  fi

  rm -f "${tmp_script}"
  echo "Error: No GUI askpass helper found (zenity/kdialog) and pkexec is unavailable." >&2
  return 1
}

wait_for_http_ready() {
  local url="$1"
  local timeout_seconds="${2:-30}"
  local start_ts now

  start_ts="$(date +%s)"
  while true; do
    if curl -fsS -m 2 -o /dev/null "${url}" >/dev/null 2>&1; then
      return 0
    fi

    now="$(date +%s)"
    if (( now - start_ts >= timeout_seconds )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_tcp_ready() {
  local url="$1"
  local py host port
  py="$(engine_python)"
  read -r host port < <("${py}" - "${url}" <<'PY'
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
host = parsed.hostname or "127.0.0.1"
port = parsed.port or (443 if parsed.scheme == "https" else 80)
print(host, port)
PY
)

  if "${py}" - "${host}" "${port}" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(1.0)
try:
    sock.connect((host, port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
raise SystemExit(0)
PY
  then
    return 0
  fi
  return 1
}

engine_socket_path() {
  local mode="$1"
  if [[ "${mode}" == "dev" ]]; then
    echo "${ROOT_DIR}/.skillpilot/temp/engine-dev.sock"
  else
    echo "${ROOT_DIR}/.skillpilot/temp/engine.sock"
  fi
}

engine_socket_running() {
  local mode="$1"
  local socket_path py
  socket_path="$(engine_socket_path "${mode}")"
  if [[ ! -S "${socket_path}" ]]; then
    return 1
  fi

  py="$(engine_python)"
  "${py}" - "${socket_path}" <<'PY'
import socket
import sys

socket_path = sys.argv[1]
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.settimeout(1.0)
try:
    client.connect(socket_path)
except OSError:
    raise SystemExit(1)
finally:
    client.close()
raise SystemExit(0)
PY
}

get_running_webui_url() {
  local mode="$1"
  if [[ "${mode}" == "dev" ]]; then
    core/bin/tool-cli get_webui_url --dev 2>/dev/null
  else
    core/bin/tool-cli get_webui_url 2>/dev/null
  fi
}

session_exists() {
  local session_name="$1"
  tmux has-session -t "${session_name}" 2>/dev/null
}

required_sessions_live() {
  local mode="$1"
  if [[ "${mode}" == "dev" ]]; then
    session_exists "sp-webui-dev" && session_exists "sp-engine-dev"
  elif ((NEXT_SERVER == 1)); then
    session_exists "sp-engine-prod" && session_exists "sp-webui-prod"
  else
    session_exists "sp-engine-prod"
  fi
}

print_startup_troubleshooting() {
  local mode="$1"
  echo "A startup tmux session exited before Skill Pilot became reachable."
  echo "Run the raw command(s) below for troubleshooting:"
  if [[ "${mode}" == "dev" ]]; then
    local dev_webui_host dev_webui_port
    dev_webui_host="$(get_service_host "webui" "development")"
    dev_webui_port="$(get_service_port "webui" "development")"
    echo "  cd ${ROOT_DIR}/core/webui && SKILL_PILOT_RUNTIME_MODE=development HOSTNAME=${dev_webui_host} PORT=${dev_webui_port} node scripts/with-timestamp-logs.js dev --webpack --hostname ${dev_webui_host} --port ${dev_webui_port}"
    echo "  cd ${ROOT_DIR} && SKILL_PILOT_RUNTIME_MODE=development uv --project core/engine run core/engine/main.py --reload --reload-dir core/engine --reload-exclude core/engine/tests"
  else
    echo "  cd ${ROOT_DIR} && SKILL_PILOT_RUNTIME_MODE=production uv --project core/engine run core/engine/main.py"
    if ((NEXT_SERVER == 1)); then
      local prod_webui_host prod_webui_port
      prod_webui_host="$(get_service_host "webui" "development")"
      prod_webui_port="$(get_service_port "webui" "development")"
      echo "  cd ${ROOT_DIR}/core/webui && SKILL_PILOT_RUNTIME_MODE=production HOSTNAME=${prod_webui_host} PORT=${prod_webui_port} node scripts/with-timestamp-logs.js start --hostname ${prod_webui_host} --port ${prod_webui_port}"
    fi
  fi
}

wait_for_service_ready_or_session_exit() {
  local mode="$1"
  local url="$2"
  local start_ts now
  local next_notice=45

  start_ts="$(date +%s)"
  while true; do
    if wait_for_tcp_ready "${url}"; then
      return 0
    fi

    if ! required_sessions_live "${mode}"; then
      return 1
    fi

    now="$(date +%s)"
    if (( now - start_ts >= next_notice )); then
      echo "Skill Pilot is still starting. The tmux session is still live, so waiting longer..."
      next_notice=$((next_notice + 30))
    fi
    sleep 1
  done
}

open_or_print_webui_url() {
  local mode="$1"
  local base_url url ready_url
  base_url="$(get_webui_base_url "${mode}")"
  if [[ -n "${AUTH_TOKEN:-}" ]]; then
    url="${base_url}?token=${AUTH_TOKEN}"
  else
    url="${base_url}"
  fi

  if [[ "${mode}" == "dev" ]]; then
    ready_url="${base_url}"
  else
    ready_url="${base_url}"
  fi

  echo ""
  if [[ "${SOURCE}" == "webui" ]]; then
    echo "Waiting for Skill Pilot to become reachable: ${ready_url}"
    if wait_for_service_ready_or_session_exit "${mode}" "${ready_url}"; then
      echo "Skill Pilot is reachable."
      echo "Opening WebUI in browser: ${url}"
      open_in_browser "${url}"
    else
      print_startup_troubleshooting "${mode}"
      return 1
    fi
    return 0
  fi

  if has_gui_env; then
    echo "Waiting for Skill Pilot to become reachable: ${ready_url}"
    if wait_for_service_ready_or_session_exit "${mode}" "${ready_url}"; then
      echo "Skill Pilot is reachable."
      echo "Opening WebUI in browser: ${url}"
      open_in_browser "${url}"
    else
      print_startup_troubleshooting "${mode}"
      return 1
    fi
  else
    echo "Waiting for Skill Pilot to become reachable: ${ready_url}"
    if wait_for_service_ready_or_session_exit "${mode}" "${ready_url}"; then
      echo "Skill Pilot is reachable."
      echo "Open this URL in your browser:"
      echo "  ${url}"
    else
      print_startup_troubleshooting "${mode}"
      return 1
    fi
  fi
}

start_session() {
  local session_name="$1"
  local command="$2"
  local replace_existing="${3:-0}"

  if tmux has-session -t "${session_name}" 2>/dev/null; then
    if [[ "${replace_existing}" == "1" ]]; then
      tmux kill-session -t "${session_name}"
      echo "Stopped existing session '${session_name}'."
    else
      echo "Session '${session_name}' already exists. Skipping."
      return
    fi
  fi

  sync_tmux_environment
  tmux new-session -d -s "${session_name}" "cd '${ROOT_DIR}' && ${command}" \; set -g status off
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
  test)
    run_engine_tests
    ;;
  doctor)
    run_doctor
    ;;
  start)
    require_tmux
    ensure_engine_venv
    if ((IS_DEV == 1)); then
      if [[ "${SOURCE}" != "webui" ]] && engine_socket_running "dev"; then
        _running_url="$(get_running_webui_url "dev")"
        echo "Skill Pilot is already running in development mode."
        if [[ -n "${_running_url}" ]]; then
          echo "Access it at:"
          echo "  ${_running_url}"
        fi
        exit 0
      fi
    elif [[ "${SOURCE}" != "webui" ]] && ((NEXT_SERVER == 0)) && engine_socket_running "prod"; then
      _running_url="$(get_running_webui_url "prod")"
      echo "Skill Pilot is already running in production mode."
      if [[ -n "${_running_url}" ]]; then
        echo "Access it at:"
          echo "  ${_running_url}"
      fi
      exit 0
    fi
    run_init_wizard_if_needed
    load_guarded_env
    # Wizard Screen 8 — Starting services
    show_screen "Starting Skill Pilot"
    echo "Launching services in tmux background sessions..."
    echo ""
    if ((IS_DEV == 1)); then
      _replace_existing_dev_sessions=0
      require_cmd pnpm
      echo "Running pnpm install for core/webui..."
      pnpm -C "${ROOT_DIR}/core/webui" install
      _dev_webui_host="$(get_service_host "webui" "development")"
      _dev_webui_port="$(get_service_port "webui" "development")"
      if [[ "${SOURCE}" == "webui" ]]; then
        _replace_existing_dev_sessions=1
      fi
      start_session "sp-webui-dev" "cd core/webui && SKILL_PILOT_RUNTIME_MODE=development HOSTNAME=${_dev_webui_host} PORT=${_dev_webui_port} node scripts/with-timestamp-logs.js dev --webpack --hostname ${_dev_webui_host} --port ${_dev_webui_port}" "${_replace_existing_dev_sessions}"
      start_session "sp-engine-dev" "SKILL_PILOT_RUNTIME_MODE=development uv --project core/engine run core/engine/main.py --reload --reload-dir core/engine --reload-exclude core/engine/tests" "${_replace_existing_dev_sessions}"
      _dev_engine_url="$(get_service_base_url "engine" "development")"
      _webui_url="$(get_webui_base_url "dev")"
      echo "  Dev engine   ->  ${_dev_engine_url%/}"
      echo "  WebUI   ->  ${_webui_url%/}  (dev mode)"
      echo ""
      echo "Use 'tmux attach -t sp-webui-dev -r' or 'tmux attach -t sp-engine-dev -r' to view logs."
    else
      _replace_existing_prod_sessions=0
      if [[ "${SOURCE}" == "webui" ]]; then
        _replace_existing_prod_sessions=1
      fi
      if ((NEXT_SERVER == 1)); then
        require_cmd pnpm
        echo "Running pnpm install for core/webui..."
        pnpm -C "${ROOT_DIR}/core/webui" install
        if [[ ! -f "${ROOT_DIR}/core/webui/.next/BUILD_ID" ]]; then
          echo "Building Next.js production server bundle (next build)..."
          pnpm -C "${ROOT_DIR}/core/webui" build
        fi
      else
        ensure_webui_release_assets
      fi
      start_session "sp-engine-prod" "SKILL_PILOT_RUNTIME_MODE=production uv --project core/engine run core/engine/main.py" "${_replace_existing_prod_sessions}"
      _engine_prod_url="$(get_service_base_url "engine" "production")"
      if ((NEXT_SERVER == 1)); then
        _prod_webui_host="$(get_service_host "webui" "development")"
        _prod_webui_port="$(get_service_port "webui" "development")"
        start_session "sp-webui-prod" "cd core/webui && SKILL_PILOT_RUNTIME_MODE=production HOSTNAME=${_prod_webui_host} PORT=${_prod_webui_port} node scripts/with-timestamp-logs.js start --hostname ${_prod_webui_host} --port ${_prod_webui_port}" "${_replace_existing_prod_sessions}"
        _webui_url="$(get_webui_base_url "prod")"
        echo "  Engine  ->  ${_engine_prod_url%/}  (production mode)"
        echo "  WebUI   ->  ${_webui_url%/}  (production mode, next start)"
        echo ""
        echo "Use 'tmux attach -t sp-engine-prod -r' or 'tmux attach -t sp-webui-prod -r' to view logs."
      else
        _engine_url="$(get_webui_base_url "prod")"
        echo "  Engine + WebUI  ->  ${_engine_url%/}  (production mode)"
        echo ""
        echo "Use 'tmux attach -t sp-engine-prod -r' to view logs."
      fi
    fi
    echo ""
    echo "To stop Skill Pilot at any time, run:"
    if ((IS_DEV == 1)); then
      echo "  ./skillpilot.sh stop --dev"
    elif ((NEXT_SERVER == 1)); then
      echo "  ./skillpilot.sh stop --next-server"
    else
      echo "  ./skillpilot.sh stop"
    fi
    if ((IS_DEV == 1)); then
      open_or_print_webui_url "dev"
    else
      open_or_print_webui_url "prod"
    fi
    ;;
  stop)
    require_tmux
    if ((IS_DEV == 1)); then
      stop_session "sp-webui-dev"
      stop_session "sp-engine-dev"
    else
      stop_session "sp-engine-prod"
      if ((NEXT_SERVER == 1)); then
        stop_session "sp-webui-prod"
      fi
    fi
    echo "Done."
    ;;
  enable)
    case "${ACTION_TARGET}" in
      human-detection)
        install_human_detection_deps
        ;;
      live-tts)
        install_live_tts_deps
        ;;
      *)
        echo "Error: unsupported enable target '${ACTION_TARGET}'."
        exit 1
        ;;
    esac
    ;;
  disable)
    case "${ACTION_TARGET}" in
      human-detection)
        uninstall_human_detection_deps
        ;;
      live-tts)
        uninstall_live_tts_deps
        ;;
      *)
        echo "Error: unsupported disable target '${ACTION_TARGET}'."
        exit 1
        ;;
    esac
    ;;
  *)
    print_help
    exit 1
    ;;
esac
