#!/usr/bin/env bash
set -euo pipefail

export HOME="${HOME:-/home/ubuntu}"
export SHELL="${SHELL:-/bin/bash}"
export PNPM_HOME="${PNPM_HOME:-${HOME}/.local/share/pnpm}"
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PNPM_HOME}:${PATH}"

APP_DIR="${SKILL_PILOT_HOME:-/home/ubuntu/skill-pilot}"
AUTH_TOKEN="${AUTH_TOKEN:-skill-pilot-docker}"
DOCKER_CONFIG_DIR="${DOCKER_CONFIG_DIR:-/usr/local/share/skill-pilot-docker-config}"

cd "${APP_DIR}"

apply_docker_config() {
  mkdir -p config

  shopt -s nullglob
  local file
  for file in "${DOCKER_CONFIG_DIR}"/*.json5; do
    cp "${file}" "config/$(basename "${file}")"
  done
  shopt -u nullglob
}

ensure_auth_env() {
  mkdir -p config

  if [[ ! -f config/.env ]]; then
    printf 'AUTH_TOKEN=%s\n' "${AUTH_TOKEN}" > config/.env
    chmod 600 config/.env || true
  fi
}

stop_skill_pilot() {
  ./skillpilot.sh stop --all >/dev/null 2>&1 || true
}

case "${1:-start}" in
  start)
    apply_docker_config
    ensure_auth_env
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
