#!/usr/bin/env bash

# --- Constants ---
SOMETHING_INSTALLED=0
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
trap cleanup EXIT
trap 'printf "\n"; warn "Installation cancelled."; exit 130' INT

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
  local input_fd="/dev/tty"
  if ! { true </dev/tty; } 2>/dev/null; then
    input_fd="/dev/stdin"
  fi
  while true; do
    read -r -p "$prompt [Y/n]: " answer <"$input_fd"
    case "${answer:-}" in
      [Yy]|[Yy][Ee][Ss]|"") return 0 ;;
      [Nn]|[Nn][Oo]) return 1 ;;
      *) warn "Please answer y or n." ;;
    esac
  done
}

# --- Shell environment refresh ---
reload_shell_env() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

  case "$(uname -s 2>/dev/null || true)" in
    Darwin) export PNPM_HOME="${PNPM_HOME:-$HOME/Library/pnpm}" ;;
    *) export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}" ;;
  esac
  export PATH="$PNPM_HOME:$PATH"

  if command -v pnpm >/dev/null 2>&1; then
    local pnpm_bin
    pnpm_bin="$(pnpm bin -g 2>/dev/null || true)"
    [ -n "$pnpm_bin" ] && export PATH="$pnpm_bin:$PATH"
  fi

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
    warn "sudo is required but not found — skipping this step."
    return 1
  fi
}

# --- Linux build tools ---
install_build_tools_linux() {
  require_sudo || return 1
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
  warn "No supported package manager found (apt-get or dnf required) — skipping build tools."
  return 1
}

# --- Package-manager dispatch ---
pkg_install() {
  local pkg="$1"
  if ! command -v brew >/dev/null 2>&1; then
    warn "Homebrew not found — cannot install '$pkg'. Skipping."
    return 1
  fi
  brew install "$pkg"
}

# --- Step runner ---
install_step() {
  local title="$1"
  local why="$2"
  local cmd_name="$3"
  local install_fn="$4"

  info "\n${BOLD}${title}${NC}"
  info "$why"

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "$title is already available."
    return 0
  fi

  if ! ask_yes_no "Install $title now?"; then
    warn "Skipping $title."
    return 0
  fi

  if ! "$install_fn"; then
    warn "$title installation failed — continuing without it."
    return 0
  fi
  SOMETHING_INSTALLED=1
  reload_shell_env

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "$title installed and available in current shell."
  else
    warn "$title installed but not visible in PATH yet. Open a new terminal if needed."
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
  export SHELL="${SHELL:-bash}"
  $CURL https://astral.sh/uv/install.sh | sh
}

install_pnpm() {
  export SHELL="${SHELL:-bash}"
  $CURL https://get.pnpm.io/install.sh | sh
}

install_playwright() {
  pnpm install -g @playwright/cli@latest
  local bin_dir
  bin_dir="$(pnpm bin -g 2>/dev/null || true)"
  [ -n "$bin_dir" ] && export PATH="$bin_dir:$PATH"
  hash -r 2>/dev/null || true
}

# --- Version checks ---
check_node_version() {
  if ! command -v node >/dev/null 2>&1; then
    return 1
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
  if ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi
  local minor
  minor="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  if [ "$minor" -lt 9 ] 2>/dev/null; then
    warn "Python 3.${minor} found — 3.9+ is required."
    return 1
  fi
  return 0
}

# --- Shell PATH persistence ---
path_contains() {
  case ":${PATH}:" in
    *":$1:"*) return 0 ;;
    *) return 1 ;;
  esac
}

setup_shell_paths() {
  local rc_files=()
  [ -f "$HOME/.bashrc" ] && rc_files+=("$HOME/.bashrc")
  [ -f "$HOME/.zshrc" ]  && rc_files+=("$HOME/.zshrc")

  # Resolve actual PNPM_HOME path
  local pnpm_home
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) pnpm_home="$HOME/Library/pnpm" ;;
    *)      pnpm_home="$HOME/.local/share/pnpm" ;;
  esac
  pnpm_home="${PNPM_HOME:-$pnpm_home}"

  # Build only the lines that are needed:
  # include a path only if the directory exists and is not already in PATH
  local lines=""
  if [ -d "$HOME/.local/bin" ] && ! path_contains "$HOME/.local/bin"; then
    lines+='export PATH="$HOME/.local/bin:$PATH"'$'\n'
  fi
  if [ -d "$pnpm_home" ] && ! path_contains "$pnpm_home"; then
    lines+="export PNPM_HOME=\"$pnpm_home\""$'\n'
    lines+='export PATH="$PNPM_HOME:$PATH"'$'\n'
  fi

  if [ -z "$lines" ]; then
    ok "All tool paths are already in PATH — no profile update needed."
    return 0
  fi

  local block=$'\n# --- Added by Skill Pilot installer ---\n'"$lines"

  local updated=0
  local manual_files=()
  for rc in "${rc_files[@]}"; do
    if grep -q "Added by Skill Pilot installer" "$rc" 2>/dev/null; then
      ok "PATH entries already present in $rc."
    elif [ ! -w "$rc" ]; then
      warn "Cannot write to $rc (permission denied) — skipping."
      manual_files+=("$rc")
    else
      printf '%s\n' "$block" >> "$rc"
      ok "Added tool PATH entries to $rc."
      updated=1
    fi
  done

  if [ "${#manual_files[@]}" -gt 0 ]; then
    warn "\nCould not update the following shell config file(s) automatically:"
    for rc in "${manual_files[@]}"; do
      warn "  $rc"
    done
    warn "\nTo set up your PATH manually, add the following lines to your shell config:"
    warn "----"
    warn "$block"
    warn "----"
    warn "Then run:  source <your-rc-file>  or open a new terminal."
  fi

  if [ "$updated" -eq 1 ]; then
    info "Run 'source ~/.bashrc' (or open a new terminal) to apply PATH changes."
  fi
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
  case "${1:-}" in
    -h|--help) usage; exit 0 ;;
  esac

  say "${BOLD}Skill Pilot Installer (macOS/Linux)${NC}"
  say ""

  reload_shell_env

  ask_yes_no "Before continuing, confirm you have one of these ready: Claude Code, OpenAI Codex, Gemini CLI, or an OpenAI/Claude-compatible API endpoint and API key" \
    || warn "Continuing anyway — you can configure an AI agent after installation."

  local os
  os="$(uname -s 2>/dev/null || true)"
  local OS_KIND
  case "$os" in
    Darwin) OS_KIND="mac" ;;
    Linux)  OS_KIND="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
      warn "Windows is not natively supported. Install WSL and re-run inside Linux for best results."
      OS_KIND="windows"
      ;;
    *)
      warn "Unrecognised OS: $os — proceeding anyway, some steps may fail."
      OS_KIND="unknown"
      ;;
  esac

  local script_path
  script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"
  local skip_clone="false"
  case "$script_path" in
    */core/engine/dev_swarm/*) skip_clone="true" ;;
  esac

  # macOS: Xcode Command Line Tools
  if [ "$OS_KIND" = "mac" ]; then
    info "\n${BOLD}Xcode Command Line Tools${NC}"
    info "Xcode CLT provides clang, make, and git — required before installing Homebrew."
    if xcode-select -p >/dev/null 2>&1; then
      ok "Xcode Command Line Tools are already installed."
    else
      if ask_yes_no "Install Xcode Command Line Tools now?"; then
        xcode-select --install 2>/dev/null || true
        warn "A system dialog has appeared. Complete the Xcode CLT installation, then press Enter."
        { read -r -p "Press Enter once Xcode CLT installation is complete..." </dev/tty; } 2>/dev/null \
          || read -r -p "Press Enter once Xcode CLT installation is complete..."
        if xcode-select -p >/dev/null 2>&1; then
          ok "Xcode Command Line Tools installed."
        else
          warn "Xcode Command Line Tools not detected yet — continuing anyway."
        fi
      else
        warn "Skipping Xcode Command Line Tools — some steps may fail without them."
      fi
    fi
  fi

  # Linux: build-essential
  if [ "$OS_KIND" = "linux" ]; then
    install_step \
      "Linux build tools (build-essential)" \
      "build-essential (gcc, make, cmake) is required before installing Homebrew on Linux." \
      "make" \
      "install_build_tools_linux"
  fi

  # Git pre-Homebrew check
  info "\n${BOLD}Git (pre-Homebrew check)${NC}"
  info "Git is required by the Homebrew installer."
  if command -v git >/dev/null 2>&1; then
    ok "Git is already available."
  else
    if [ "$OS_KIND" = "linux" ]; then
      if ask_yes_no "Install git now via system package manager?"; then
        if command -v apt-get >/dev/null 2>&1; then
          if is_root; then apt-get install -y -qq git; else sudo apt-get install -y -qq git; fi
        elif command -v dnf >/dev/null 2>&1; then
          if is_root; then dnf install -y -q git; else sudo dnf install -y -q git; fi
        fi
      fi
    fi
    if command -v git >/dev/null 2>&1; then
      ok "Git installed."
    else
      warn "git is not available — Homebrew install may fail."
    fi
  fi

  install_step \
    "Homebrew" \
    "Homebrew is used as a package manager on macOS and Linux." \
    "brew" \
    "install_homebrew"

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

  # Node.js
  info "\n${BOLD}Node.js${NC}"
  info "Node.js v18+ is required to run JavaScript tooling used in Skill Pilot."
  if check_node_version; then
    ok "Node.js is already available and meets version requirements."
  else
    if ask_yes_no "Install latest LTS Node.js with pnpm env use --global lts?"; then
      if pnpm env use --global lts; then
        SOMETHING_INSTALLED=1
        reload_shell_env
        if command -v node >/dev/null 2>&1; then
          ok "Node.js installed and available."
        else
          warn "Node.js installed but not visible in PATH yet — open a new terminal if needed."
        fi
      else
        warn "Node.js installation failed — continuing without it."
      fi
    else
      warn "Skipping Node.js."
    fi
  fi

  # Python 3
  info "\n${BOLD}Python 3${NC}"
  info "Python 3.9+ is required for engine and automation tasks."
  if check_python_version; then
    ok "Python 3 is already available and meets version requirements."
  else
    if ask_yes_no "Install latest Python with uv python install?"; then
      if uv python install; then
        SOMETHING_INSTALLED=1
        reload_shell_env
        if command -v python3 >/dev/null 2>&1; then
          ok "Python 3 installed and available."
        else
          warn "Python 3 installed but not visible in PATH yet — open a new terminal if needed."
        fi
      else
        warn "Python 3 installation failed — continuing without it."
      fi
    else
      warn "Skipping Python 3."
    fi
  fi

  install_step \
    "tmux" \
    "tmux supports robust long-running terminal workflows and background sessions." \
    "tmux" \
    "install_tmux"

  install_step \
    "Playwright CLI" \
    "Playwright CLI enables browser automation used by project skills and testing." \
    "playwright-cli" \
    "install_playwright"

  if [ "$SOMETHING_INSTALLED" -eq 1 ]; then
    setup_shell_paths
  fi

  # Clone repository
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

  local default_dir="$HOME/workspace/skill-pilot"
  info "\n${BOLD}Choose install location${NC}"
  info "Default path: $default_dir"
  local install_base
  if ask_yes_no "Install to $default_dir?"; then
    install_base="$default_dir"
  else
    local input_fd="/dev/tty"
    { true </dev/tty; } 2>/dev/null || input_fd="/dev/stdin"
    if read -r -e -i "$default_dir" -p "Please update the path: " install_base <"$input_fd" 2>/dev/null; then
      : # readline pre-fill succeeded
    else
      printf "Please update the path [%s]: " "$default_dir" >/dev/tty 2>&1 || printf "Please update the path [%s]: " "$default_dir"
      IFS= read -r install_base <"$input_fd" || true
    fi
    install_base="${install_base:-$default_dir}"
    info "Using: $install_base"
  fi

  local clone_dir="$install_base"
  local parent_dir
  parent_dir="$(dirname "$clone_dir")"

  if [ ! -d "$parent_dir" ]; then
    if ask_yes_no "Directory '$parent_dir' does not exist. Create it?"; then
      mkdir -p "$parent_dir" || { warn "Could not create $parent_dir — skipping clone."; return 0; }
    else
      warn "Skipping repository clone."
      return 0
    fi
  fi

  if [ ! -w "$parent_dir" ]; then
    warn "Directory is not writable: $parent_dir — skipping clone."
    return 0
  fi

  info "\nRepository setup"
  info "Cloning Skill Pilot into: $clone_dir"
  if ! ask_yes_no "Proceed with git clone?"; then
    warn "Skipping repository clone."
    return 0
  fi

  if [ -d "$clone_dir/.git" ]; then
    warn "Repository already exists at $clone_dir"
    if ! ask_yes_no "Reuse existing repository and continue?"; then
      warn "Skipping repository setup."
      return 0
    fi
  else
    if ! git clone --depth 1 https://github.com/x-school-academy/skill-pilot "$clone_dir"; then
      warn "git clone failed — skipping remaining setup."
      return 0
    fi
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
