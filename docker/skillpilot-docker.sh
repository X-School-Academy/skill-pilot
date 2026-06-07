#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="${IMAGE_NAME:-skill-pilot:ubuntu-arm64}"
CONTAINER_NAME="${CONTAINER_NAME:-skill-pilot}"
AUTH_TOKEN="${AUTH_TOKEN:-skill-pilot-docker}"

PORT_ARGS=(
  -p 13000:3000
  -p 13001:3001
  -p 13002:3002
  -p 13003:3003
  -p 15000:5000
  -p 18000:8000
  -p 18080:8080
)

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  build      Build the Ubuntu ARM64 Skill Pilot image
  start      Start the container and Skill Pilot
  stop       Stop Skill Pilot and the container
  restart    Stop, then start the container and Skill Pilot
  sp-start   Start or restart Skill Pilot inside the running container
  sp-stop    Stop Skill Pilot inside the running container
  logs       Follow container logs
  shell      Open a bash shell in the running container
  status     Show container status
  rm         Remove the stopped container

Environment:
  IMAGE_NAME      Default: ${IMAGE_NAME}
  CONTAINER_NAME  Default: ${CONTAINER_NAME}
  AUTH_TOKEN      Default: ${AUTH_TOKEN}
EOF
}

container_exists() {
  docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_running() {
  [[ "$(docker container inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)" == "true" ]]
}

ensure_container_running() {
  if container_running; then
    return
  fi

  if container_exists; then
    docker start "${CONTAINER_NAME}" >/dev/null
  else
    docker run -d \
      --name "${CONTAINER_NAME}" \
      "${PORT_ARGS[@]}" \
      -e AUTH_TOKEN="${AUTH_TOKEN}" \
      "${IMAGE_NAME}" >/dev/null
  fi
}

start_skill_pilot() {
  docker exec -d \
    -e AUTH_TOKEN="${AUTH_TOKEN}" \
    "${CONTAINER_NAME}" \
    /usr/local/bin/skill-pilot-entrypoint start >/dev/null
}

case "${1:-}" in
  build)
    docker build --platform linux/arm64 -t "${IMAGE_NAME}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}"
    ;;
  start)
    ensure_container_running
    start_skill_pilot
    echo "Skill Pilot container: ${CONTAINER_NAME}"
    echo "WebUI: http://127.0.0.1:13001/?token=${AUTH_TOKEN}"
    ;;
  stop)
    if container_running; then
      docker exec "${CONTAINER_NAME}" /usr/local/bin/skill-pilot-entrypoint stop || true
      docker stop "${CONTAINER_NAME}"
    fi
    ;;
  restart)
    "$0" stop || true
    "$0" start
    ;;
  sp-start)
    ensure_container_running
    start_skill_pilot
    echo "WebUI: http://127.0.0.1:13001/?token=${AUTH_TOKEN}"
    ;;
  sp-stop)
    docker exec "${CONTAINER_NAME}" /usr/local/bin/skill-pilot-entrypoint stop
    ;;
  logs)
    docker logs -f "${CONTAINER_NAME}"
    ;;
  shell)
    docker exec -it "${CONTAINER_NAME}" /bin/bash
    ;;
  status)
    docker ps -a --filter "name=^/${CONTAINER_NAME}$"
    ;;
  rm)
    docker rm "${CONTAINER_NAME}"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
