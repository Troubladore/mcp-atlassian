#!/usr/bin/env bash
# Claude Code launcher for mcp-atlassian in a sandboxed Docker container
# with network egress filtering via Squid proxy.
#
# Full parity with the Claude Desktop MCPB extension security model:
#   - Container isolation (cap-drop=ALL, read-only, no-new-privileges)
#   - Network egress filtering (only *.atlassian.net, *.jira.com, *.atlassian.com)
#   - Resource limits (256MB memory, 0.5 CPU)
#   - No host filesystem access
#
# Usage:
#   claude mcp add --scope user atlassian -- /path/to/claude-code-launcher.sh
#
# Prerequisites:
#   - Docker installed and running
#   - ~/.config/mcp-atlassian/.env with credentials (see below)
#   - Proxy image built (auto-builds on first run)
#
# .env file format:
#   ATLASSIAN_URL=https://your-instance.atlassian.net
#   ATLASSIAN_EMAIL=your.email@example.com
#   ATLASSIAN_API_TOKEN=your_api_token
#   TOOLSETS=all
#   READ_ONLY_MODE=false
#   ALLOW_DELETE_TOOLS=false

set -euo pipefail

# --- Configuration ---
IMAGE="ghcr.io/troubladore/mcp-atlassian:v0.11.16"
PROXY_IMAGE="eruditis/atlassian-proxy:latest"
PROXY_CONTAINER_NAME="eruditis-atlassian-proxy"
NETWORK_NAME="eruditis-atlassian-net"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${HOME}/.config/mcp-atlassian/.env"

# --- Logging (to stderr so it doesn't interfere with MCP stdio) ---
log() { echo "[eruditis-atlassian] $*" >&2; }

# --- Verify Docker is available ---
if ! command -v docker >/dev/null 2>&1; then
  log "ERROR: 'docker' not found on PATH."
  log "  If using WSL, ensure Docker Desktop is running and WSL integration is enabled."
  log "  Docker Desktop → Settings → Resources → WSL integration → enable this distro."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  log "ERROR: Docker daemon is not running."
  log "  Start Docker Desktop and wait for it to be ready."
  exit 1
fi

# --- Load credentials ---
if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: Credential file not found: $ENV_FILE"
  log ""
  log "Create it with:"
  log "  mkdir -p ~/.config/mcp-atlassian"
  log "  cat > ~/.config/mcp-atlassian/.env << 'EOF'"
  log "ATLASSIAN_URL=https://your-instance.atlassian.net"
  log "ATLASSIAN_EMAIL=your.email@example.com"
  log "ATLASSIAN_API_TOKEN=your_api_token"
  log "TOOLSETS=all"
  log "READ_ONLY_MODE=false"
  log "ALLOW_DELETE_TOOLS=false"
  log "EOF"
  log "  chmod 600 ~/.config/mcp-atlassian/.env"
  exit 1
fi

# Source the env file
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Validate required vars
if [[ -z "${ATLASSIAN_URL:-}" || -z "${ATLASSIAN_EMAIL:-}" || -z "${ATLASSIAN_API_TOKEN:-}" ]]; then
  log "ERROR: Missing required config in $ENV_FILE"
  log "  ATLASSIAN_URL: ${ATLASSIAN_URL:+set}"
  log "  ATLASSIAN_EMAIL: ${ATLASSIAN_EMAIL:+set}"
  log "  ATLASSIAN_API_TOKEN: ${ATLASSIAN_API_TOKEN:+set}"
  exit 1
fi

# Defaults
TOOLSETS="${TOOLSETS:-all}"
READ_ONLY_MODE="${READ_ONLY_MODE:-false}"
ALLOW_DELETE_TOOLS="${ALLOW_DELETE_TOOLS:-false}"
CONFLUENCE_SPACES_FILTER="${CONFLUENCE_SPACES_FILTER:-}"
JIRA_PROJECTS_FILTER="${JIRA_PROJECTS_FILTER:-}"

# Normalize URLs
BASE_URL="${ATLASSIAN_URL%/}"
if [[ "$BASE_URL" == *"/wiki" ]]; then
  CONFLUENCE_URL="$BASE_URL"
  JIRA_URL="${BASE_URL%/wiki}"
else
  CONFLUENCE_URL="${BASE_URL}/wiki"
  JIRA_URL="$BASE_URL"
fi

# --- Ensure Docker network exists ---
if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  log "Creating Docker network: $NETWORK_NAME"
  docker network create "$NETWORK_NAME" >/dev/null
fi

# --- Ensure proxy image is built ---
if ! docker image inspect "$PROXY_IMAGE" >/dev/null 2>&1; then
  log "Building Atlassian filtering proxy image..."
  docker build -t "$PROXY_IMAGE" "${SCRIPT_DIR}/proxy" >&2
fi

# --- Ensure proxy container is running ---
if ! docker ps --filter "name=${PROXY_CONTAINER_NAME}" --filter "status=running" --format "{{.Names}}" | grep -q "^${PROXY_CONTAINER_NAME}$"; then
  # Remove stale container if it exists
  docker rm -f "$PROXY_CONTAINER_NAME" 2>/dev/null || true

  log "Starting Atlassian filtering proxy..."
  docker run -d \
    --name "$PROXY_CONTAINER_NAME" \
    --restart=unless-stopped \
    --network="$NETWORK_NAME" \
    --cap-drop=ALL \
    --security-opt no-new-privileges:true \
    --read-only \
    --tmpfs /var/cache/squid:noexec,nosuid,size=64m,uid=31,gid=31 \
    --tmpfs /var/log/squid:noexec,nosuid,size=16m,uid=31,gid=31 \
    --tmpfs /var/run/squid:noexec,nosuid,size=8m,uid=31,gid=31 \
    "$PROXY_IMAGE" >/dev/null

  # Wait for proxy to be ready
  for i in $(seq 1 10); do
    if docker exec "$PROXY_CONTAINER_NAME" nc -z 127.0.0.1 3128 2>/dev/null; then
      log "Proxy ready."
      break
    fi
    sleep 0.5
  done
else
  log "Proxy already running."
fi

# --- Build Docker run args ---
DOCKER_ARGS=(
  run --rm -i
  --network="$NETWORK_NAME"
  --cap-drop=ALL
  --security-opt no-new-privileges:true
  --read-only
  --tmpfs /tmp:noexec,nosuid,size=64m
  --memory=256m
  --cpus=0.5

  # Credentials
  -e "CONFLUENCE_URL=${CONFLUENCE_URL}"
  -e "CONFLUENCE_USERNAME=${ATLASSIAN_EMAIL}"
  -e "CONFLUENCE_API_TOKEN=${ATLASSIAN_API_TOKEN}"
  -e "JIRA_URL=${JIRA_URL}"
  -e "JIRA_USERNAME=${ATLASSIAN_EMAIL}"
  -e "JIRA_API_TOKEN=${ATLASSIAN_API_TOKEN}"

  # Tool config
  -e "TOOLSETS=${TOOLSETS}"
  -e "READ_ONLY_MODE=${READ_ONLY_MODE}"
  -e "ALLOW_DELETE_TOOLS=${ALLOW_DELETE_TOOLS}"

  # Network egress filtering
  -e "HTTP_PROXY=http://${PROXY_CONTAINER_NAME}:3128"
  -e "HTTPS_PROXY=http://${PROXY_CONTAINER_NAME}:3128"
  -e "NO_PROXY=localhost,127.0.0.1"
)

# Optional filters
[[ -n "$CONFLUENCE_SPACES_FILTER" ]] && DOCKER_ARGS+=(-e "CONFLUENCE_SPACES_FILTER=${CONFLUENCE_SPACES_FILTER}")
[[ -n "$JIRA_PROJECTS_FILTER" ]] && DOCKER_ARGS+=(-e "JIRA_PROJECTS_FILTER=${JIRA_PROJECTS_FILTER}")

# Image
DOCKER_ARGS+=("$IMAGE")

log "Launching MCP server (TOOLSETS=${TOOLSETS}, READ_ONLY=${READ_ONLY_MODE})..."

# --- Run (stdin/stdout pass through for MCP stdio transport) ---
exec docker "${DOCKER_ARGS[@]}"
