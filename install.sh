#!/usr/bin/env bash

# --- Constants ---
SOMETHING_INSTALLED=0
FAILED_INSTALLS=()
UPDATED_RC_FILES=()
AVAILABLE_AI_AGENTS=()
NEEDS_LOCAL_BIN_PATH=0
NEEDS_PNPM_HOME_PATH=0
NEEDS_BREW_SHELLENV=0
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

press_any_key() {
  local msg="${1:-Press any key to continue, or Ctrl-C to exit.}"
  printf '%b' "${BOLD}${msg}${NC} "
  local input_fd="/dev/tty"
  { true </dev/tty; } 2>/dev/null || input_fd="/dev/stdin"
  read -r -s -n 1 <"$input_fd" || true
  printf '\n'
}

show_screen() {
  say ""
  say "${BOLD}============================================================${NC}"
  say "${BOLD}  $1${NC}"
  say "${BOLD}============================================================${NC}"
  say ""
}

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
  1. Install Homebrew, Git, curl, wget, uv, pnpm, Node.js, Python 3, tmux, ffmpeg
  2. Clone the Skill Pilot repository when needed
  3. Install supported AI code agent CLIs
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
    local base_pkgs=(build-essential git curl python3 make g++ cmake pkg-config)
    if is_root; then
      apt-get update -qq
      apt-get install -y -qq "${base_pkgs[@]}"
    else
      sudo apt-get update -qq
      sudo apt-get install -y -qq "${base_pkgs[@]}"
    fi
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    local base_pkgs=(gcc gcc-c++ make cmake python3 git curl)
    if is_root; then
      dnf install -y -q "${base_pkgs[@]}"
    else
      sudo dnf install -y -q "${base_pkgs[@]}"
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
  local edu_text="$2"
  local cmd_name="$3"
  local install_fn="$4"
  local path_requirement="${5:-}"

  show_screen "$title"
  say "$edu_text"
  say ""

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "Good — ${title} is already installed."
    press_any_key
    return 0
  fi

  press_any_key "Press any key and I will install it for you, or Ctrl-C to exit."

  if ! "$install_fn"; then
    warn "${title} installation failed — continuing without it."
    FAILED_INSTALLS+=("${title}")
    return 0
  fi
  SOMETHING_INSTALLED=1
  mark_path_requirement "$path_requirement"
  reload_shell_env

  if command -v "$cmd_name" >/dev/null 2>&1; then
    ok "${title} installed and available."
  else
    warn "${title} installed but not yet visible in PATH. Open a new terminal if needed."
  fi
}

# --- Individual install functions ---
install_homebrew() {
  local tmpscript
  tmpscript="$(mktemp)" || { warn "Cannot create temp file for Homebrew installer."; return 1; }
  if ! $CURL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh > "$tmpscript" \
     || [ ! -s "$tmpscript" ]; then
    rm -f "$tmpscript"
    warn "Failed to download Homebrew installer."
    return 1
  fi
  NONINTERACTIVE=1 /bin/bash "$tmpscript"
  local rc=$?
  rm -f "$tmpscript"
  return $rc
}

install_git()   { pkg_install git; }
install_curl()  { pkg_install curl; }
install_wget()  { pkg_install wget; }
install_tmux()  { pkg_install tmux; }
install_ffmpeg() { pkg_install ffmpeg; }

install_gxmessage_linux() {
  if command -v gxmessage >/dev/null 2>&1; then
    return 0
  fi
  require_sudo || return 1
  if ! command -v apt-get >/dev/null 2>&1; then
    warn "apt-get not found — skipping gxmessage installation."
    return 1
  fi
  if is_root; then
    apt-get update -qq
    apt-get install -y -qq gxmessage
  else
    sudo apt-get update -qq
    sudo apt-get install -y -qq gxmessage
  fi
}

install_uv() {
  export SHELL="${SHELL:-bash}"
  local tmpscript
  tmpscript="$(mktemp)" || { warn "Cannot create temp file for uv installer."; return 1; }
  if ! $CURL https://astral.sh/uv/install.sh > "$tmpscript" || [ ! -s "$tmpscript" ]; then
    rm -f "$tmpscript"
    warn "Failed to download uv installer."
    return 1
  fi
  sh "$tmpscript"; local rc=$?
  rm -f "$tmpscript"
  return $rc
}

install_pnpm() {
  export SHELL="${SHELL:-bash}"
  local tmpscript
  tmpscript="$(mktemp)" || { warn "Cannot create temp file for pnpm installer."; return 1; }
  if ! $CURL https://get.pnpm.io/install.sh > "$tmpscript" || [ ! -s "$tmpscript" ]; then
    rm -f "$tmpscript"
    warn "Failed to download pnpm installer."
    return 1
  fi
  sh "$tmpscript"; local rc=$?
  rm -f "$tmpscript"
  return $rc
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
  local version_ok
  version_ok="$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 9) else 0)')"
  if [ "${version_ok}" != "1" ]; then
    local ver
    ver="$(python3 -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")')"
    warn "Python ${ver} found — 3.9+ is required."
    return 1
  fi
  return 0
}

# --- Shell PATH persistence ---
mark_path_requirement() {
  case "${1:-}" in
    local_bin) NEEDS_LOCAL_BIN_PATH=1 ;;
    pnpm_home) NEEDS_PNPM_HOME_PATH=1 ;;
    brew_shellenv) NEEDS_BREW_SHELLENV=1 ;;
    both)
      NEEDS_LOCAL_BIN_PATH=1
      NEEDS_PNPM_HOME_PATH=1
      ;;
    all)
      NEEDS_LOCAL_BIN_PATH=1
      NEEDS_PNPM_HOME_PATH=1
      NEEDS_BREW_SHELLENV=1
      ;;
  esac
}

profile_has_token() {
  local rc="$1"
  local token="$2"
  grep -F "$token" "$rc" 2>/dev/null | grep -qv '^[[:space:]]*#'
}

profile_has_local_bin_path() {
  local rc="$1"
  profile_has_token "$rc" '$HOME/.local/bin' \
    || profile_has_token "$rc" "$HOME/.local/bin" \
    || profile_has_token "$rc" '~/.local/bin'
}

profile_has_pnpm_home_decl() {
  local rc="$1"
  local pnpm_home="$2"
  profile_has_token "$rc" 'export PNPM_HOME=' \
    || profile_has_token "$rc" 'PNPM_HOME=' \
    || profile_has_token "$rc" "$pnpm_home"
}

profile_has_pnpm_path() {
  local rc="$1"
  local pnpm_home="$2"
  profile_has_token "$rc" '$PNPM_HOME' \
    || profile_has_token "$rc" "$pnpm_home"
}

resolve_brew_bin() {
  if command -v brew >/dev/null 2>&1; then
    command -v brew
    return 0
  fi
  if [ -x /opt/homebrew/bin/brew ]; then
    printf '%s\n' /opt/homebrew/bin/brew
    return 0
  fi
  if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    printf '%s\n' /home/linuxbrew/.linuxbrew/bin/brew
    return 0
  fi
  if [ -x /usr/local/bin/brew ]; then
    printf '%s\n' /usr/local/bin/brew
    return 0
  fi
  return 1
}

profile_has_brew_shellenv() {
  local rc="$1"
  local brew_bin="$2"
  profile_has_token "$rc" 'brew shellenv' \
    || profile_has_token "$rc" "$brew_bin shellenv"
}

setup_shell_paths() {
  local rc_files=()
  [ -f "$HOME/.bashrc" ] && rc_files+=("$HOME/.bashrc")
  [ -f "$HOME/.zshrc" ]  && rc_files+=("$HOME/.zshrc")

  if [ "$NEEDS_LOCAL_BIN_PATH" -eq 0 ] && [ "$NEEDS_PNPM_HOME_PATH" -eq 0 ] && [ "$NEEDS_BREW_SHELLENV" -eq 0 ]; then
    ok "No profile PATH updates needed for tools installed in this run."
    return 0
  fi

  # Resolve actual PNPM_HOME path
  local pnpm_home
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) pnpm_home="$HOME/Library/pnpm" ;;
    *)      pnpm_home="$HOME/.local/share/pnpm" ;;
  esac
  pnpm_home="${PNPM_HOME:-$pnpm_home}"

  local can_add_local_bin=0
  local can_add_pnpm_home=0
  local can_add_brew_shellenv=0
  local brew_bin=""

  if [ "$NEEDS_LOCAL_BIN_PATH" -eq 1 ]; then
    if [ -d "$HOME/.local/bin" ]; then
      can_add_local_bin=1
    else
      warn "Skipping profile PATH update: $HOME/.local/bin does not exist."
    fi
  fi

  if [ "$NEEDS_PNPM_HOME_PATH" -eq 1 ]; then
    if [ -d "$pnpm_home" ]; then
      can_add_pnpm_home=1
    else
      warn "Skipping profile PATH update: $pnpm_home does not exist."
    fi
  fi

  if [ "$NEEDS_BREW_SHELLENV" -eq 1 ]; then
    if brew_bin="$(resolve_brew_bin)"; then
      can_add_brew_shellenv=1
    else
      warn "Skipping profile Homebrew update: brew binary not found."
    fi
  fi

  if [ "$can_add_local_bin" -eq 0 ] && [ "$can_add_pnpm_home" -eq 0 ] && [ "$can_add_brew_shellenv" -eq 0 ]; then
    ok "No existing install path directories need profile updates."
    return 0
  fi

  if [ "${#rc_files[@]}" -eq 0 ]; then
    warn "No shell profile file found (.bashrc or .zshrc) to update automatically."
    warn "Add the following lines to your shell config manually:"
    warn "────────────────────────────────────────────"
    if [ "$can_add_local_bin" -eq 1 ]; then
      warn 'export PATH="$HOME/.local/bin:$PATH"'
    fi
    if [ "$can_add_pnpm_home" -eq 1 ]; then
      warn "export PNPM_HOME=\"$pnpm_home\""
      warn 'export PATH="$PNPM_HOME:$PATH"'
    fi
    if [ "$can_add_brew_shellenv" -eq 1 ]; then
      warn "eval \"\$($brew_bin shellenv)\""
    fi
    warn "────────────────────────────────────────────"
    warn "Then run: source <rc-file> (example: source ~/.zshrc or ~/.bashrc)"
    warn "Or open a new terminal to apply changes."
    return 0
  fi

  local manual_files=()
  local manual_need_local_bin=0
  local manual_need_pnpm_home_decl=0
  local manual_need_pnpm_path=0
  local manual_need_brew_shellenv=0
  for rc in "${rc_files[@]}"; do
    local lines=""

    if [ "$can_add_local_bin" -eq 1 ]; then
      if profile_has_local_bin_path "$rc"; then
        ok "PATH entry for ~/.local/bin already present in $rc."
      else
        lines+='export PATH="$HOME/.local/bin:$PATH"'$'\n'
      fi
    fi

    if [ "$can_add_pnpm_home" -eq 1 ]; then
      if profile_has_pnpm_home_decl "$rc" "$pnpm_home"; then
        :
      else
        lines+="export PNPM_HOME=\"$pnpm_home\""$'\n'
      fi

      if profile_has_pnpm_path "$rc" "$pnpm_home"; then
        :
      else
        lines+='export PATH="$PNPM_HOME:$PATH"'$'\n'
      fi
    fi

    if [ "$can_add_brew_shellenv" -eq 1 ]; then
      if profile_has_brew_shellenv "$rc" "$brew_bin"; then
        ok "Homebrew shellenv already present in $rc."
      else
        lines+="eval \"\$($brew_bin shellenv)\""$'\n'
      fi
    fi

    if [ -z "$lines" ]; then
      ok "No PATH updates needed in $rc."
      continue
    fi

    if [ ! -w "$rc" ]; then
      warn "Cannot write to $rc (permission denied) — skipping."
      manual_files+=("$rc")
      if printf '%s' "$lines" | grep -Fq 'export PATH="$HOME/.local/bin:$PATH"'; then
        manual_need_local_bin=1
      fi
      if printf '%s' "$lines" | grep -Fq 'export PNPM_HOME='; then
        manual_need_pnpm_home_decl=1
      fi
      if printf '%s' "$lines" | grep -Fq 'export PATH="$PNPM_HOME:$PATH"'; then
        manual_need_pnpm_path=1
      fi
      if printf '%s' "$lines" | grep -Fq 'brew shellenv'; then
        manual_need_brew_shellenv=1
      fi
      continue
    fi

    local block=$'\n# --- Added by Skill Pilot installer ---\n'"$lines"
    printf '%s\n' "$block" >> "$rc"
    ok "Updated $rc with missing tool PATH entries."
    UPDATED_RC_FILES+=("$rc")
  done

  if [ "${#manual_files[@]}" -gt 0 ]; then
    warn "\nCould not update the following shell config file(s) automatically:"
    for rc in "${manual_files[@]}"; do
      warn "  $rc"
    done
    warn "\nAdd the following lines to your shell config manually:"
    warn "────────────────────────────────────────────"
    if [ "$manual_need_local_bin" -eq 1 ]; then
      warn 'export PATH="$HOME/.local/bin:$PATH"'
    fi
    if [ "$manual_need_pnpm_home_decl" -eq 1 ]; then
      warn "export PNPM_HOME=\"$pnpm_home\""
    fi
    if [ "$manual_need_pnpm_path" -eq 1 ]; then
      warn 'export PATH="$PNPM_HOME:$PATH"'
    fi
    if [ "$manual_need_brew_shellenv" -eq 1 ]; then
      warn "eval \"\$($brew_bin shellenv)\""
    fi
    warn "────────────────────────────────────────────"
    warn "Then run: source <rc-file> (example: source ~/.zshrc or ~/.bashrc))"
    warn "Or open a new terminal to apply changes."
  fi
}

# --- Internal profile for skillpilot.sh ---
write_skillpilot_profile() {
  local profile_dir="$HOME/.skillpilot"
  local profile_file="${profile_dir}/.profile"
  mkdir -p "$profile_dir" 2>/dev/null || true

  local pnpm_home_line
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) pnpm_home_line='export PNPM_HOME="${PNPM_HOME:-$HOME/Library/pnpm}"' ;;
    *)      pnpm_home_line='export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"' ;;
  esac

  local brew_env=""
  if [ -x /opt/homebrew/bin/brew ]; then
    brew_env='eval "$(/opt/homebrew/bin/brew shellenv)"'
  elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    brew_env='eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"'
  elif [ -x /usr/local/bin/brew ]; then
    brew_env='eval "$(/usr/local/bin/brew shellenv)"'
  fi

  {
    echo '# --- Added by Skill Pilot installer ---'
    echo 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"'
    echo "$pnpm_home_line"
    echo 'export PATH="$PNPM_HOME:$PATH"'
    [ -n "$brew_env" ] && echo "$brew_env"
  } > "$profile_file"
}

# --- Git branch setup ---
setup_branches() {
  info "\nSetting up git branches..."
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"

  if git show-ref --verify --quiet "refs/heads/user"; then
    ok "Branch 'user' already exists."
  else
    git branch user
    ok "Created branch 'user'."
  fi

  if [ "$current_branch" != "user" ]; then
    git checkout user
    ok "Switched to branch 'user' (work branch)."
  else
    ok "Already on branch 'user' (work branch)."
  fi
}

detect_available_ai_agents() {
  AVAILABLE_AI_AGENTS=()

  if command -v claude >/dev/null 2>&1; then
    AVAILABLE_AI_AGENTS+=("claude")
  fi
  if command -v copilot >/dev/null 2>&1; then
    AVAILABLE_AI_AGENTS+=("copilot")
  fi
  if command -v codex >/dev/null 2>&1; then
    AVAILABLE_AI_AGENTS+=("codex")
  fi
  if command -v gemini >/dev/null 2>&1; then
    AVAILABLE_AI_AGENTS+=("gemini")
  fi
  if command -v opencode >/dev/null 2>&1; then
    AVAILABLE_AI_AGENTS+=("opencode")
  fi
}

ai_agent_label() {
  case "$1" in
    claude)   echo "Claude Code        — free plan available" ;;
    copilot)  echo "GitHub Copilot CLI — free plan available" ;;
    gemini)   echo "Google Gemini CLI  — free tier available" ;;
    codex)    echo "OpenAI Codex CLI   — free tier available" ;;
    opencode) echo "OpenCode           — free tier available" ;;
    *)        echo "$1" ;;
  esac
}

ai_agent_install_cmd() {
  case "$1" in
    claude)   echo "curl -fsSL https://claude.ai/install.sh | bash" ;;
    copilot)  echo "pnpm install -g @github/copilot" ;;
    gemini)   echo "pnpm install -g @google/gemini-cli" ;;
    codex)    echo "pnpm install -g @openai/codex" ;;
    opencode) echo "pnpm install -g opencode-ai" ;;
    *)        echo "" ;;
  esac
}

install_ai_code_agents() {
  local agents_to_install=("$@")
  local agent pkg installed_count=0

  for agent in "${agents_to_install[@]}"; do
    case "$agent" in
      claude)
        if ! command -v curl >/dev/null 2>&1; then
          warn "curl not found — cannot install Claude Code automatically."
          FAILED_INSTALLS+=("Claude Code CLI")
          continue
        fi
        info "Installing Claude Code..."
        if curl -fsSL https://claude.ai/install.sh | bash; then
          SOMETHING_INSTALLED=1
          mark_path_requirement "local_bin"
          installed_count=$((installed_count + 1))
        else
          warn "Claude Code installation failed."
          FAILED_INSTALLS+=("Claude Code CLI")
        fi
        ;;
      copilot)
        pkg="@github/copilot"
        ;;
      gemini)
        pkg="@google/gemini-cli"
        ;;
      codex)
        pkg="@openai/codex"
        ;;
      opencode)
        pkg="opencode-ai"
        ;;
      *)
        warn "Unknown AI agent '${agent}' — skipping."
        continue
        ;;
    esac

    if [ "$agent" = "claude" ]; then
      continue
    fi

    if ! command -v pnpm >/dev/null 2>&1; then
      warn "pnpm not found — cannot install ${pkg} automatically."
      FAILED_INSTALLS+=("${agent} CLI")
      continue
    fi

    info "Installing ${pkg}..."
    if pnpm install -g "${pkg}"; then
      SOMETHING_INSTALLED=1
      mark_path_requirement "pnpm_home"
      installed_count=$((installed_count + 1))
    else
      warn "${pkg} installation failed."
      FAILED_INSTALLS+=("${agent} CLI")
    fi
  done

  if [ "$installed_count" -gt 0 ]; then
    reload_shell_env
  fi
}

run_ai_code_agent_install_step() {
  local all_agents=(claude copilot gemini codex opencode)
  local missing_agents=()
  local agent found installed installed_before

  show_screen "AI Agent CLI Tools"
  say "Skill Pilot works with these AI code agent CLIs:"
  say ""
  say "  claude    Claude Code by Anthropic"
  say "  copilot   GitHub Copilot CLI"
  say "  codex     OpenAI Codex CLI"
  say "  gemini    Google Gemini CLI"
  say "  opencode  OpenCode (open source, OpenAI-compatible)"
  say ""
  say "Checking what you have installed..."
  say ""

  detect_available_ai_agents
  installed_before=("${AVAILABLE_AI_AGENTS[@]}")
  for agent in "${all_agents[@]}"; do
    found=0
    for installed in "${AVAILABLE_AI_AGENTS[@]}"; do
      if [ "$installed" = "$agent" ]; then
        found=1
        break
      fi
    done
    if [ "$found" -eq 1 ]; then
      say "  ${GREEN}$(printf '%-10s  installed' "${agent}")${NC}"
    else
      say "  ${YELLOW}$(printf '%-10s  not found' "${agent}")${NC}"
      missing_agents+=("${agent}")
    fi
  done

  if [ "${#missing_agents[@]}" -eq 0 ]; then
    say ""
    ok "All supported AI agent CLIs are already installed."
    press_any_key
    return 0
  fi

  show_screen "Install AI Code Agents"
  say "The following AI code agents are not yet installed:"
  say ""
  for agent in "${missing_agents[@]}"; do
    say "  $(printf '%-10s  %s' "${agent}" "$(ai_agent_label "${agent}")")"
  done
  say ""
  say "Press any key and I will install the missing ones for you:"
  say ""
  for agent in "${missing_agents[@]}"; do
    say "  $(ai_agent_install_cmd "${agent}")"
  done
  say ""

  if [ "${#installed_before[@]}" -eq 0 ]; then
    warn "At least one AI agent CLI is required to continue."
    press_any_key "Press any key to install the missing AI agents, or Ctrl-C to exit."
    install_ai_code_agents "${missing_agents[@]}"
    detect_available_ai_agents
    if [ "${#AVAILABLE_AI_AGENTS[@]}" -eq 0 ]; then
      err "No AI agent CLI is available after installation attempt."
      err "Please install one manually and re-run: bash install.sh"
      return 1
    fi
    return 0
  fi

  press_any_key "Press any key to install the missing AI agents, or Ctrl-C to skip."
  install_ai_code_agents "${missing_agents[@]}" || true
  detect_available_ai_agents
}

# --- Next-steps reminder ---
print_next_steps() {
  if [ "${#UPDATED_RC_FILES[@]}" -eq 0 ]; then
    return 0
  fi
  say ""
  say "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  say "${BOLD}  Action required — reload your shell${NC}"
  say "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  say "  New tool paths were added to your shell profile file(s)."
  say "  To activate commands in this terminal now, run:"
  say ""
  for rc in "${UPDATED_RC_FILES[@]}"; do
    say "    ${BOLD}source $rc${NC}"
  done
  say ""
  say "  Or open a new terminal window instead."
  say "  New commands will work after either step."
  say "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# --- Main ---
main() {
  case "${1:-}" in
    -h|--help) usage; exit 0 ;;
  esac

  # Screen 1 — Welcome
  show_screen "Welcome to Skill Pilot AI Agent"
  say "You are about to set up a Codeware environment — a living"
  say "workspace where you and AI work together every day."
  say ""
  say "This is not a regular app you download and click."
  say "You are installing a habitat for an AI worker."
  say ""
  say "  Traditional software:  Human -> UI -> Software -> Fixed result"
  say "  Codeware:              Human -> AI -> Codebase -> Evolving result"
  say ""
  say "Skill Pilot lets you vibe code, learn, build products, and"
  say "explore what AI can really do — side by side, in your own"
  say "terminal."
  press_any_key

  reload_shell_env

  local os OS_KIND
  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin) OS_KIND="mac" ;;
    Linux)  OS_KIND="linux" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
      # Screen 2 — Windows
      show_screen "Windows Detected"
      say "Windows is not natively compatible with the AI and developer"
      say "tools that Skill Pilot depends on."
      say ""
      say "The good news: Microsoft ships a free Linux layer for Windows"
      say "called WSL (Windows Subsystem for Linux). It lets you run a"
      say "full Linux terminal inside Windows."
      say ""
      say "Step 1 — Open this link in your browser and follow the guide:"
      say "  https://learn.microsoft.com/en-us/windows/wsl/install"
      say ""
      say "Step 2 — When asked to choose a Linux distribution, pick:"
      say "  Ubuntu  (most widely used by developers and in the cloud)"
      say ""
      say "Step 3 — Once WSL is installed, open the Ubuntu terminal and"
      say "  run the Skill Pilot install command from there."
      press_any_key "Press any key to exit, then install WSL first."
      exit 0
      ;;
    *)
      warn "Unrecognised OS: $os — proceeding anyway, some steps may fail."
      OS_KIND="unknown"
      ;;
  esac

  local current_dir source_checkout="false"
  current_dir="$(pwd -P)"
  if [ -f "$current_dir/core/bin/keys-safe-guard" ]; then
    source_checkout="true"
  fi

  # Screen 3 — macOS only: Xcode Command Line Tools
  if [ "$OS_KIND" = "mac" ]; then
    show_screen "Xcode Command Line Tools"
    say "AI needs a small free toolkit from Apple called \"Xcode Command Line Tools\"."
    say ""
    say "What it includes:"
    say "  - clang   : a compiler that turns code into programs"
    say "  - make    : a tool for building software step by step"
    say "  - git     : version control (we will explain this soon)"
    say ""
    say "Think of it as the foundation layer before any AI/developer"
    say "tools can be installed on a Mac."
    say ""
    if xcode-select -p >/dev/null 2>&1; then
      ok "Good — Xcode Command Line Tools are already on your Mac."
      press_any_key
    else
      press_any_key "Press any key and I will start the installation for you, or Ctrl-C to exit."
      xcode-select --install 2>/dev/null || true
      warn "A system dialog has appeared. Complete the Xcode CLT installation,"
      warn "then come back here and press Enter."
      { read -r -p "" </dev/tty; } 2>/dev/null || read -r -p ""
      if xcode-select -p >/dev/null 2>&1; then
        ok "Xcode Command Line Tools installed."
      else
        warn "Xcode Command Line Tools not detected yet — continuing anyway."
      fi
    fi
  fi

  # Screen 4 — Linux only: Build Tools
  if [ "$OS_KIND" = "linux" ]; then
    show_screen "Linux Build Tools"
    say "AI needs a set of compilers and utilities on Linux."
    say ""
    say "What is being installed:"
    say "  - gcc / g++ : compilers that turn code into programs"
    say "  - make      : a build coordinator"
    say "  - cmake     : used by many tools and libraries"
    say "  - pkg-config: helps programs find other libraries"
    say ""
    say "Think of it as the foundation layer before any AI/developer"
    say "tools can be installed on Linux."
    say ""
    if command -v make >/dev/null 2>&1; then
      ok "Good — build tools are already available."
      press_any_key
    else
      press_any_key "Press any key and I will install them for you, or Ctrl-C to exit."
      install_build_tools_linux || warn "Build tools installation failed — continuing anyway."
    fi
  fi

  # Git pre-Homebrew check (silent)
  if ! command -v git >/dev/null 2>&1 && [ "$OS_KIND" = "linux" ]; then
    if command -v apt-get >/dev/null 2>&1; then
      if is_root; then apt-get install -y -qq git 2>/dev/null; else sudo apt-get install -y -qq git 2>/dev/null; fi
    elif command -v dnf >/dev/null 2>&1; then
      if is_root; then dnf install -y -q git 2>/dev/null; else sudo dnf install -y -q git 2>/dev/null; fi
    fi
  fi

  # Screen 5 — Homebrew
  install_step \
    "Homebrew — Your Package Manager" \
    "$(printf '%s\n%s\n\n%s\n%s\n%s\n%s\n%s' \
      "A package manager is like an app store for developer tools," \
      "but operated entirely from the terminal." \
      "Why Homebrew?" \
      "  - Installs software without needing admin/root password" \
      "  - Keeps everything in its directory (safe, clean)" \
      "  - Used by most AI agent skills in Skill Pilot" \
      "  - Works on both macOS and Linux")" \
    "brew" \
    "install_homebrew" \
    "brew_shellenv"

  # Screen 6 — uv
  install_step \
    "uv — Fast Python Manager" \
    "$(printf '%s\n%s\n%s\n\n%s\n\n%s\n%s\n%s\n%s\n\n%s' \
      "Python is AI's first language." \
      "AI agents use Python to run calculations, call APIs," \
      "process files, and do anything an LLM alone cannot do." \
      "uv is a modern tool for managing Python. Compare:" \
      "  Old way (pip):  slow installs, shared packages between" \
      "                  projects, easy to break things" \
      "  uv:             very fast, each project gets its own" \
      "                  isolated packages, saves disk space" \
      "Skill Pilot's engine is built with Python + uv.")" \
    "uv" \
    "install_uv" \
    "local_bin"

  # Screen 7 — Python 3
  show_screen "Python 3 — AI's First Language"
  say "Python is the language most widely used in AI research and"
  say "engineering. Skill Pilot's engine, LLM routing, and most"
  say "automation tools are written in Python."
  say ""
  say "We need Python version 3.9 or newer."
  say "uv will install the right version automatically."
  say ""
  if check_python_version; then
    ok "Good — Python 3 is already installed and up to date."
    press_any_key
  else
    press_any_key "Press any key and I will install the latest Python 3 for you, or Ctrl-C to exit."
    if uv python install; then
      SOMETHING_INSTALLED=1
      reload_shell_env
      ok "Python 3 installed."
    else
      warn "Python 3 installation failed — continuing without it."
    fi
  fi

  # Screen 8 — pnpm
  install_step \
    "pnpm — Fast Node.js Package Manager" \
    "$(printf '%s\n%s\n\n%s\n%s\n\n%s\n%s\n%s\n%s\n%s' \
      "Node.js is the most popular runtime for building websites," \
      "AI agents, and cloud services." \
      "Skill Pilot's web interface is built with Next.js — a" \
      "framework that runs on Node.js." \
      "pnpm manages Node.js packages. Compare:" \
      "  Old way (npm):  downloads a full copy of packages for" \
      "                  every project — uses a lot of disk space" \
      "  pnpm:           uses smart links to share packages across" \
      "                  projects — faster, much less disk space")" \
    "pnpm" \
    "install_pnpm" \
    "pnpm_home"

  # Screen 9 — Node.js
  show_screen "Node.js — JavaScript Runtime"
  say "Node.js lets JavaScript code run on your computer (not just"
  say "in a browser). It powers:"
  say ""
  say "  - Skill Pilot's web interface (Next.js)"
  say "  - Many AI agent tools and CLI programs"
  say "  - Modern cloud services and APIs"
  say ""
  say "We need Node.js version 18 or newer."
  say "pnpm will install the right version for you."
  say ""
  say "  LTS = Long-Term Support — the stable, recommended version"
  say "  that gets security updates for several years."
  say ""
  if check_node_version; then
    ok "Good — Node.js is already installed and up to date."
    press_any_key
  else
    press_any_key "Press any key and I will install the latest LTS Node.js for you, or Ctrl-C to exit."
    if pnpm env use --global lts; then
      SOMETHING_INSTALLED=1
      mark_path_requirement "pnpm_home"
      reload_shell_env
      ok "Node.js installed."
    else
      warn "Node.js installation failed — continuing without it."
    fi
  fi

  # Screen 10 — tmux
  install_step \
    "tmux — Your Shared Terminal Space" \
    "$(printf '%s\n\n%s\n%s\n\n%s\n%s\n%s\n\n%s\n%s' \
      "tmux is one of the most important tools in Skill Pilot." \
      "Normally, when you close a terminal window, everything" \
      "running inside it stops. tmux keeps sessions alive in the" \
      "background, even when you close the window." \
      "More importantly for Skill Pilot:" \
      "  tmux lets you and AI share the same terminal view." \
      "  You can both see what is happening at the same time —" \
      "  great for debugging and working together." \
      "  You watch AI work." \
      "  AI can see your terminal output too.")" \
    "tmux" \
    "install_tmux"

  # Screen 11 — wget
  install_step \
    "wget — File Downloader" \
    "$(printf '%s\n%s\n%s\n\n%s\n%s' \
      "wget is a command-line tool for downloading files from the" \
      "internet. Many AI agent skills use wget to fetch datasets," \
      "models, configuration files, and other resources." \
      "curl can also download files, but wget handles large files" \
      "and retries broken downloads more gracefully.")" \
    "wget" \
    "install_wget"

  # Screen 12 — ffmpeg
  install_step \
    "ffmpeg — Media Toolkit" \
    "$(printf '%s\n%s\n%s\n\n%s\n%s\n%s' \
      "ffmpeg is the command-line toolkit Skill Pilot uses for" \
      "video and audio processing tasks such as transcoding," \
      "merging clips, extracting frames, and generating thumbnails." \
      "Several media and workflow features depend on it being" \
      "available in PATH." \
      "If ffmpeg is missing, this installer will add it with" \
      "Homebrew.")" \
    "ffmpeg" \
    "install_ffmpeg"

  # Screen 12 — gxmessage (Linux only)
  if [ "$OS_KIND" = "linux" ]; then
    install_step \
      "gxmessage — Linux Confirmation Dialogs" \
      "$(printf '%s\n%s\n\n%s\n%s' \
        "Skill Pilot uses gxmessage on Linux when it needs a simple" \
        "desktop confirmation window for actions that should pause." \
        "This keeps confirmations lightweight and avoids extra Python" \
        "GUI dependencies for headless or mixed environments.")" \
      "gxmessage" \
      "install_gxmessage_linux"
  fi

  local workspace_dir=""
  if [ "$source_checkout" = "true" ]; then
    workspace_dir="$current_dir"
    warn "Detected source checkout in the current directory via core/bin/keys-safe-guard; skipping git clone and branch setup."
  else
    # Screen 13 — Choose install location
    show_screen "Choose Install Location"
    say "The ~/  symbol means your home folder."
    say "On macOS:  /Users/your-username/"
    say "On Linux:  /home/your-username/"
    say ""
    say "This is your personal space on the computer. Installing"
    say "here does not affect other users and requires no special"
    say "permissions."
    say ""
    say "We recommend installing under your home folder:"
    say ""

    local opt1="$HOME/workspace/skill-pilot"
    local opt2
    opt2="$(pwd)/skill-pilot"
    local install_base
    local input_fd="/dev/tty"
    { true </dev/tty; } 2>/dev/null || input_fd="/dev/stdin"

    say "  ${BOLD}1)${NC} ~/workspace/skill-pilot          ${BLUE}(recommended)${NC}"
    say "     ${BLUE}-> $opt1${NC}"
    say ""
    say "  ${BOLD}2)${NC} Current folder / skill-pilot"
    say "     ${BLUE}-> $opt2${NC}"
    say ""
    say "  ${BOLD}3)${NC} Enter a custom path (you specify the full project folder)"
    say ""

    local choice
    while true; do
      read -r -p "Enter your choice [1/2/3]: " choice <"$input_fd"
      case "${choice:-}" in
        1)
          install_base="$opt1"
          ok "Install location: $install_base"
          break
          ;;
        2)
          install_base="$opt2"
          ok "Install location: $install_base"
          break
          ;;
        3)
          local custom_base
          printf "\nEnter the full installation path (this will be the project folder): " >/dev/tty 2>&1 \
            || printf "\nEnter the full installation path (this will be the project folder): "
          IFS= read -r custom_base <"$input_fd" || true
          custom_base="${custom_base%/}"
          if [ -z "$custom_base" ]; then
            warn "No path entered — using default: $opt1"
            install_base="$opt1"
          else
            install_base="$custom_base"
          fi
          ok "Install location: $install_base"
          break
          ;;
        *) warn "Please enter 1, 2, or 3." ;;
      esac
    done

    local clone_dir="$install_base"
    local parent_dir
    parent_dir="$(dirname "$clone_dir")"

    if [ ! -d "$parent_dir" ]; then
      say "Creating directory: $parent_dir"
      mkdir -p "$parent_dir" || { warn "Could not create $parent_dir — skipping clone."; return 0; }
    fi

    if [ ! -w "$parent_dir" ]; then
      warn "Directory is not writable: $parent_dir — skipping clone."
      return 0
    fi

    # Screen 14 — Git clone
    show_screen "Downloading Skill Pilot (git clone)"
    say "What is git?"
    say "  git is a version control tool — it tracks every change"
    say "  made to a codebase over time. Like \"Track Changes\" in a"
    say "  document, but for code."
    say ""
    say "What is git clone?"
    say "  git clone downloads a full copy of a codebase from the"
    say "  internet to your computer. Unlike a zip download, a clone"
    say "  keeps a connection to the original — so you can receive"
    say "  future updates."
    say ""
    say "  In Skill Pilot, updates to the codeware (the stable"
    say "  release layer) come in as git updates, just like any"
    say "  normal software update."
    say ""
    say "Cloning Skill Pilot into: $clone_dir"
    press_any_key "Press any key to start the download, or Ctrl-C to exit."

    if [ -d "$clone_dir/.git" ]; then
      warn "Repository already exists at $clone_dir — reusing existing repository."
    else
      if ! git clone --depth 1 https://github.com/x-school-academy/skill-pilot "$clone_dir"; then
        warn "git clone failed — skipping remaining setup."
        return 0
      fi
    fi

    cd "$clone_dir"
    workspace_dir="$clone_dir"

    # Screen 15 — Git branches
    show_screen "Setting Up Your Workspace Branches"
    say "git uses branches to manage parallel versions of the same"
    say "codebase."
    say ""
    say "Skill Pilot uses two branches during normal local setup:"
    say ""
    say "  codeware  The stable release layer — maintained by the"
    say "            Skill Pilot team. Think of this as the \"main\""
    say "            software release. You keep it clean and use it"
    say "            as your update source."
    say ""
    say "  user      Your personal workspace — where you and AI"
    say "            make all your daily changes. This branch is"
    say "            yours to edit freely."
    say ""
    say "Contribution branches are created only when you are ready"
    say "to prepare a clean contribution back to the official repo."
    say ""
    say "Normal flow:"
    say "  codeware -> user       (you receive updates)"
    say ""
    say "Contribution flow, only when needed:"
    say "  user -> feature branch from upstream/contrib -> pull request"
    press_any_key "Press any key to create the 'user' branch and switch to it now."

    setup_branches
  fi

  run_ai_code_agent_install_step || return 1

  if [ "$SOMETHING_INSTALLED" -eq 1 ]; then
    setup_shell_paths
  fi

  # Write internal profile for skillpilot.sh to source silently
  write_skillpilot_profile

  # Screen 16 — PATH environment setup (only shown when new tools were installed)
  if [ "$SOMETHING_INSTALLED" -eq 1 ]; then
    show_screen "Saving Tool Paths"
    say "When you install a tool, your terminal needs to know"
    say "where to find it. This is called the PATH."
    say ""
    say "The PATH settings for the tools just installed have been"
    say "added to your shell profile. The installer detected your"
    say "shell and updated the right file automatically."
    say ""
    say "New terminal windows will pick this up automatically."
    say ""
    say "To use the newly installed tools right now in this terminal,"
    say "run the command shown below (your file may be different):"
    say ""
    if [ "${#UPDATED_RC_FILES[@]}" -gt 0 ]; then
      for rc in "${UPDATED_RC_FILES[@]}"; do
        say "  source $rc"
      done
    else
      say "  source ~/.zshrc   or   source ~/.bashrc"
    fi
    say ""
    say "Or simply open a new terminal window — either works."
    press_any_key
  fi

  # Screen 17 — Installation complete
  show_screen "Installation Complete"
  if [ "${#FAILED_INSTALLS[@]}" -eq 0 ]; then
    ok "All tools are installed and your workspace is ready."
  else
    warn "Setup finished, but the following tools could not be installed:"
    for t in "${FAILED_INSTALLS[@]}"; do
      warn "  - ${t}"
    done
    say ""
    say "You can install missing tools manually and re-run:"
    say "  bash install.sh"
    say ""
    say "Your workspace is otherwise ready — continuing."
  fi
  say ""
  say "Next step — start Skill Pilot:"
  say ""
  say "1. Activate new tool paths in this terminal:"
  if [ "${#UPDATED_RC_FILES[@]}" -gt 0 ]; then
    for rc in "${UPDATED_RC_FILES[@]}"; do
      say "     source $rc"
    done
  else
    say "     (no new paths needed — all tools were already set up)"
  fi
  say "   (or open a new terminal window instead)"
  say ""
  say "2. Run the Skill Pilot setup wizard:"
  say "     cd $workspace_dir"
  say "     ./skillpilot.sh"
  say ""
  say "The wizard will:"
  say "  - Explain ports, addresses, and network settings"
  say "  - Detect your installed AI agent CLIs"
  say "  - Set up your default AI provider"
  say "  - Start Skill Pilot for the first time"
  press_any_key "Press any key to exit the installer."
}

main "$@"
