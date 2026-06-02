#!/usr/bin/env bash
set -euo pipefail

export HOME="${HOME:-/home/ubuntu}"
export SHELL="${SHELL:-/bin/bash}"
export PNPM_HOME="${PNPM_HOME:-${HOME}/.local/share/pnpm}"
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PNPM_HOME}:${PATH}"

APP_DIR="${SKILL_PILOT_HOME:-/home/ubuntu/skill-pilot}"
AUTH_TOKEN="${AUTH_TOKEN:-skill-pilot-docker}"

cd "${APP_DIR}"

ensure_default_config() {
  mkdir -p config

  if [[ ! -f config/settings.json5 ]]; then
    cat > config/settings.json5 <<'EOF_SETTINGS'
{
  security: {
    schedules: { sandbox: true, auto: true, network: true },
    newSession: { sandbox: false, auto: false, network: true },
    remoteBot: { sandbox: true, auto: true, network: false },
    devSwarm: { sandbox: true, auto: true, network: true },
    skillAgent: { sandbox: true, auto: true, network: true },
  },
  services: {
    engine: {
      host: "0.0.0.0",
      production: { port: 3001 },
      development: { port: 3002 },
    },
    webui: {
      host: "0.0.0.0",
      development: { port: 3003 },
    },
    live_avatar: {
      server_url: "ws://127.0.0.1:8008",
    },
    chrome_proxy: {
      enabled: false,
      listen_host: "127.0.0.1",
      listen_port: 9223,
      wait_tunnel_timeout_s: 10,
    },
  },
  turn: {
    urls: "",
    username: "",
    password: "",
  },
}
EOF_SETTINGS
  fi

  python3 - <<'PY'
from pathlib import Path

path = Path("config/settings.json5")
text = path.read_text(encoding="utf-8")
text = text.replace('host: "127.0.0.1"', 'host: "0.0.0.0"')
text = text.replace("host: '127.0.0.1'", "host: '0.0.0.0'")
text = text.replace('"host": "127.0.0.1"', '"host": "0.0.0.0"')
path.write_text(text, encoding="utf-8")
PY

  if [[ -f config/ai_providers.json5 ]]; then
    python3 - <<'PY'
from pathlib import Path

path = Path("config/ai_providers.json5")
text = path.read_text(encoding="utf-8")
text = text.replace("llm: 'claude'", "llm: 'opencode'")
text = text.replace('"llm": "claude"', '"llm": "opencode"')
path.write_text(text, encoding="utf-8")
PY
  fi

  if [[ ! -f config/.env ]]; then
    {
      printf 'ONLY_ALLOW_HTTPS=0\n'
      printf 'AUTH_TOKEN=%s\n' "${AUTH_TOKEN}"
    } > config/.env
    chmod 600 config/.env || true
  fi
}

stop_skill_pilot() {
  ./skillpilot.sh stop --all >/dev/null 2>&1 || true
}

case "${1:-start}" in
  start)
    ensure_default_config
    stop_skill_pilot
    ./skillpilot.sh start
    echo "Skill Pilot is running. Access it at http://localhost:3001/?token=${AUTH_TOKEN}"
    trap stop_skill_pilot TERM INT
    while tmux has-session -t sp-engine-prod 2>/dev/null; do
      sleep 5
    done
    echo "Skill Pilot tmux session exited."
    exit 1
    ;;
  stop)
    stop_skill_pilot
    ;;
  shell)
    exec /bin/bash
    ;;
  *)
    exec "$@"
    ;;
esac
