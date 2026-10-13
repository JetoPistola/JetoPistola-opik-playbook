#!/usr/bin/env bash
# Bring up Dify (pinned to release 1.17.1) and configure it headlessly.
# Idempotent: safe to re-run; each step checks before it creates.
#
# Requires: Docker running and OPENAI_API_KEY (shell or repo-root .env). Traces go to a
# local Opik on the host by default; see .env.example for Opik Cloud.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$HERE/dify-docker"

# Load keys from the repo-root .env, then a local .env, if they exist.
for envfile in "$HERE/../.env" "$HERE/.env"; do
  if [ -f "$envfile" ]; then
    set -a; . "$envfile"; set +a
  fi
done

# Dify's web UI and APIs are served by its nginx on this port.
DIFY_PORT="${DIFY_PORT:-8090}"

# 1. Create dify-docker/.env from the vendored upstream template on first run.
#    Only two lines are appended: a stable compose project name and the port.
if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/env.example" "$DOCKER_DIR/.env"
  {
    echo ""
    echo "# --- dify-gym-membership-assistant overrides ---"
    echo "COMPOSE_PROJECT_NAME=dify-gym-membership-assistant"
    echo "EXPOSE_NGINX_PORT=$DIFY_PORT"
  } >> "$DOCKER_DIR/.env"
  echo "Created dify-docker/.env (port $DIFY_PORT)"
fi

# 2. Start the stack (first run pulls ~10 images; takes a few minutes).
echo "Starting the Dify stack..."
docker compose -f "$DOCKER_DIR/docker-compose.yaml" --project-directory "$DOCKER_DIR" up -d

# 3. Configure everything through the console API: admin account, OpenAI
#    plugin + credential, app import from the committed DSL, Opik tracing,
#    and a service API key for demo.sh.
#    Opik touchpoint: configure_dify.py points tracing at host.docker.internal:5173
#    (a local Opik, empty API key) by default; DIFY_OPIK_URL/OPIK_API_KEY override it.
DIFY_URL="http://localhost:$DIFY_PORT" python3 "$HERE/configure_dify.py"

echo ""
echo "Dify UI:  http://localhost:$DIFY_PORT  (login: frontdesk@ironleaf.example / IronleafGym2026)"
echo "Teardown: docker compose -f dify-docker/docker-compose.yaml --project-directory dify-docker down"
echo "          (add -v to also delete the databases and start fresh next time)"
