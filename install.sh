#!/usr/bin/env bash
set -euo pipefail

# --- Constants ---
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

CURL="curl -fsSL --proto =https --tlsv1.2"

# --- Output helpers ---
say() { printf "%b\n" "$*"; }
info() { say "${BLUE}$*${NC}"; }
warn() { say "${YELLOW}$*${NC}"; }
err() { say "${RED}$*${NC}"; }
ok() { say "${GREEN}$*${NC}"; }

# --- Trap for clean exit ---
cleanup() {
  local rc=$?
  if [ $rc -ne 0 ] && [ $rc -ne 130 ]; then
    err "\nInstallation did not complete (exit code $rc)."
    err "Fix the issue above and re-run: bash install.sh"
  fi
}
trap cleanup EXIT INT

# --- Usage ---
usage() {
  cat <<EOF
Usage: bash install.sh [OPTIONS]

Install Skill Pilot and its dependencies on macOS or Linux.

Options:
  -h, --help    Show this help message and exit

Steps performed:
  1. Install Homebrew, Git, curl, uv, pnpm, Node.js, Python 3, tmux
  2. Install Playwright CLI
  3. Clone the Skill Pilot repository
EOF
}

# --- Prompt helpers ---
ask_yes_no() {
  local prompt="$1"
  local answer
  while true; do
    read -r -p "$prompt [y/N]: " answer </dev/tty
    case "${answer:-}" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo]|"") return 1 ;;
      *) warn "Please answer y or n." ;;
    esac
  done
}

require_yes_or_exit() {
  local prompt="$1"
  if ! ask_yes_no "$prompt"; then
    warn "Installer stopped by user."
    exit 1
  fi
}

# --- Shell environment refresh ---
reload_shell_env() {
  # Prepend known installer directories to PATH (avoid sourcing shell profiles
  # which can trigger cross-shell side effects).
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

  case "$(uname -s 2>/dev/null || true)" in
    Darwin) export PNPM_HOME="${PNPM_HOME:-$HOME/Library/pnpm}" ;;
    *) export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}" ;;
  esac
  export PATH="$PNPM_HOME:$PATH"

  # Homebrew: apply shellenv if installed
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi

  hash -r 2>/dev/null || true
}

# --- Sudo helpers ---
is_root() { [ "$(id -u)" = "0" ]; }

require_sudo() {
  if is_root; then return 0; fi
  if ! command -v sudo >/dev/null 2>&1; then
    err "sudo is required but not found. Please run as root or install sudo."
    exit 1
  fi
}

# --- Linux build tools ---
install_build_tools_linux() {
  require_sudo
  if command -v apt-get >/dev/null 2>&1; then
    if is_root; then
      apt-get update -qq
      apt-get install -y -qq build-essential git curl python3 make g++ cmake
    else
      sudo apt-get update -qq
      sudo apt-get install -y -qq build-essential git curl python3 make g++ cmake
    fi
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    if is_root; then
      dnf install -y -q gcc gcc-c++ make cmake python3 git curl
    else
      sudo dnf install -y -q gcc gcc-c++ make cmake python3 git curl
    fi
    return 0
  fi
  err "No supported package manager found (apt-get or dnf required)."
  exit 1
}

# --- Package-manager dispatch ---
pkg_install() {
  local pkg="$1"
  if ! command -v brew >/dev/null 2>&1; then
    err "Homebrew is required to install '$pkg', but 'brew' was not found."
    err "Please complete the Homebrew step, then re-run: bash install.sh"
    exit 1
  fi
  brew install "$pkg"
}

# --- Step runner (no eval) ---
install_step() {
  local title="$1"
  local why="$2"
  local cmd_name="$3"          # command to check availability
  local install_fn="$4"        # function name to call for install

  info "\n${BOLD}${title}${NC}"
  info "$why"

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "$title is already available."
    return 0
  fi

  require_yes_or_exit "Install now?"
  "$install_fn"
  reload_shell_env

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "$title installed and available in current shell."
  else
    err "$title installation finished, but it is not visible in current shell PATH."
    err "Open a new terminal and run this installer again."
    exit 1
  fi
}

# --- Individual install functions ---
install_homebrew() {
  NONINTERACTIVE=1 /bin/bash -c "$($CURL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

install_git()   { pkg_install git; }
install_curl()  { pkg_install curl; }
install_tmux()  { pkg_install tmux; }

install_uv() {
  $CURL https://astral.sh/uv/install.sh | sh
}

install_pnpm() {
  $CURL https://get.pnpm.io/install.sh | sh
}

install_playwright() {
  pnpm install -g @playwright/cli@latest
}

# --- Version checks ---
check_node_version() {
  # Require Node.js >= 18
  if ! command -v node >/dev/null 2>&1; then
    return 1  # not installed
  fi
  local major
  major="$(node -e 'console.log(process.versions.node.split(".")[0])')"
  if [ "$major" -lt 18 ] 2>/dev/null; then
    warn "Node.js v${major}.x found — v18+ is required."
    return 1
  fi
  return 0
}

check_python_version() {
  # Require Python >= 3.9
  if ! command -v python3 >/dev/null 2>&1; then
    return 1  # not installed
  fi
  local minor
  minor="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  if [ "$minor" -lt 9 ] 2>/dev/null; then
    warn "Python 3.${minor} found — 3.9+ is required."
    return 1
  fi
  return 0
}

# --- Git branch setup ---
setup_branches() {
  info "\nSetting up git branches..."
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"

  for branch in contrib user; do
    if git show-ref --verify --quiet "refs/heads/$branch"; then
      ok "Branch '$branch' already exists."
    else
      git branch "$branch"
      ok "Created branch '$branch'."
    fi
  done

  if [ "$current_branch" != "user" ]; then
    git checkout user
    ok "Switched to branch 'user' (work branch)."
  else
    ok "Already on branch 'user' (work branch)."
  fi
}

# --- Main ---
main() {
  # Parse flags
  case "${1:-}" in
    -h|--help) usage; exit 0 ;;
  esac

  say "${BOLD}Skill Pilot Installer (macOS/Linux)${NC}"
  say ""

  require_yes_or_exit "Before continuing, confirm you have one of these ready: Claude Code, OpenAI Codex, Gemini CLI, or an OpenAI/Claude-compatible API endpoint and API key"

  local os
  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin) OS_KIND="mac" ;;
    Linux) OS_KIND="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
      err "Windows is not supported by this script."
      err "Please install WSL first, then run this installer inside Linux."
      exit 1
      ;;
    *)
      err "Unsupported OS: $os"
      err "This installer supports only macOS and Linux."
      exit 1
      ;;
  esac

  local script_path
  script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"
  local skip_clone="false"
  case "$script_path" in
    */core/engine/dev_swarm/*) skip_clone="true" ;;
  esac

  # macOS: install Xcode Command Line Tools before Homebrew (provides clang/make/git)
  if [ "$OS_KIND" = "mac" ]; then
    info "\n${BOLD}Xcode Command Line Tools${NC}"
    info "Xcode CLT provides clang, make, and git — required before installing Homebrew."
    if xcode-select -p >/dev/null 2>&1; then
      ok "Xcode Command Line Tools are already installed."
    else
      require_yes_or_exit "Install Xcode Command Line Tools now?"
      xcode-select --install 2>/dev/null || true
      warn "A system dialog has appeared. Complete the Xcode CLT installation, then press Enter."
      read -r -p "Press Enter once Xcode CLT installation is complete..." </dev/tty
      if xcode-select -p >/dev/null 2>&1; then
        ok "Xcode Command Line Tools installed."
      else
        err "Xcode Command Line Tools are not ready."
        err "Complete the dialog and re-run: bash install.sh"
        exit 1
      fi
    fi
  fi

  # Linux: install build-essential before Homebrew (required to compile packages)
  if [ "$OS_KIND" = "linux" ]; then
    install_step \
      "Linux build tools (build-essential)" \
      "build-essential (gcc, make, cmake) is required before installing Homebrew on Linux." \
      "make" \
      "install_build_tools_linux"
  fi

  install_step \
    "Homebrew" \
    "Homebrew is used as a package manager on macOS and Linux." \
    "brew" \
    "install_homebrew"

  install_step \
    "Git" \
    "Git is required to clone the Skill Pilot repository." \
    "git" \
    "install_git"

  install_step \
    "curl" \
    "curl downloads official install scripts for core tools." \
    "curl" \
    "install_curl"

  install_step \
    "uv" \
    "uv manages Python runtimes and fast Python tooling used by this project." \
    "uv" \
    "install_uv"

  install_step \
    "pnpm" \
    "pnpm manages Node.js packages and installs Playwright CLI." \
    "pnpm" \
    "install_pnpm"

  # --- Node.js (with version check) ---
  info "\n${BOLD}Node.js${NC}"
  info "Node.js v18+ is required to run JavaScript tooling used in Skill Pilot."
  if check_node_version; then
    ok "Node.js is already available and meets version requirements."
  else
    require_yes_or_exit "Install latest LTS Node.js with pnpm env use --global lts?"
    pnpm env use --global lts
    reload_shell_env
    if ! command -v node >/dev/null 2>&1; then
      err "Node.js is not available after install."
      exit 1
    fi
    ok "Node.js installed and available."
  fi

  # --- Python 3 (with version check) ---
  info "\n${BOLD}Python 3${NC}"
  info "Python 3.9+ is required for engine and automation tasks."
  if check_python_version; then
    ok "Python 3 is already available and meets version requirements."
  else
    require_yes_or_exit "Install latest Python with uv python install?"
    uv python install
    reload_shell_env
    if ! command -v python3 >/dev/null 2>&1; then
      err "Python 3 is not available after install."
      exit 1
    fi
    ok "Python 3 installed and available."
  fi

  install_step \
    "tmux" \
    "tmux supports robust long-running terminal workflows and background sessions." \
    "tmux" \
    "install_tmux"

  install_step \
    "Playwright CLI" \
    "Playwright CLI enables browser automation used by project skills and testing." \
    "playwright" \
    "install_playwright"

  # --- Clone repository ---
  if [ "$skip_clone" = "true" ]; then
    warn "Detected installer path under 'core/engine/dev_swarm'; skipping repository clone step."
    ok "Installation bootstrap completed."
    say ""
    say "Current directory: $(pwd)"
    if [ -x "./skillpilot.sh" ]; then
      setup_branches
      say ""
      info "Running: ./skillpilot.sh help"
      ./skillpilot.sh help
    else
      warn "Skipping './skillpilot.sh help' because ./skillpilot.sh is not executable in current directory."
    fi
    return 0
  fi

  info "\n${BOLD}Choose install location${NC}"
  read -r -p "Enter installation directory (default: \$HOME/workspace/skill-pilot): " install_base </dev/tty
  install_base="${install_base:-$HOME/workspace/skill-pilot}"

  # If user entered a directory that isn't already skill-pilot, append it
  local clone_dir="$install_base"

  local parent_dir
  parent_dir="$(dirname "$clone_dir")"

  if [ ! -d "$parent_dir" ]; then
    require_yes_or_exit "Directory '$parent_dir' does not exist. Create it?"
    mkdir -p "$parent_dir"
  fi

  if [ ! -w "$parent_dir" ]; then
    err "Directory is not writable: $parent_dir"
    exit 1
  fi

  info "\nRepository setup"
  info "Cloning Skill Pilot into: $clone_dir"
  require_yes_or_exit "Proceed with git clone?"

  if [ -d "$clone_dir/.git" ]; then
    warn "Repository already exists at $clone_dir"
    require_yes_or_exit "Reuse existing repository and continue?"
  else
    git clone --depth 1 https://github.com/x-school-academy/skill-pilot "$clone_dir"
  fi

  cd "$clone_dir"
  ok "Installation bootstrap completed."
  say ""
  say "Next directory: $(pwd)"
  setup_branches
  say ""
  info "Running: ./skillpilot.sh help"
  ./skillpilot.sh help
}

main "$@"
