#!/usr/bin/env bash
# Headless bootstrap for the volunteer-screening workflow:
#   1. build and start n8n with Opik's OpenTelemetry hooks
#   2. claim the instance (local owner account) and mint an n8n API key
#   3. create the OpenAI credential from $OPENAI_API_KEY at runtime
#   4. import workflow/volunteer-screening.json and activate it
#
# Needs docker, curl and python3. Keys come from the shell or the repo-root .env.
set -euo pipefail
cd "$(dirname "$0")"

N8N_URL="http://localhost:5678"
OWNER_EMAIL="coordinator@example.com"   # local demo account only
OWNER_PASSWORD="Pantry-demo-42"

# Walk up to the repo-root .env, if there is one.
dir="$PWD"
while [ "$dir" != "/" ]; do
  if [ -f "$dir/.env" ]; then set -a; . "$dir/.env"; set +a; break; fi
  dir="$(dirname "$dir")"
done
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (shell or repo-root .env)}"
export OPIK_WORKSPACE="${OPIK_WORKSPACE:-default}"
# Opik touchpoint: these feed the OTLP headers in docker-compose.yml. Without the
# right workspace/auth, spans are rejected or land in the wrong place.
# Opik Cloud needs an Authorization header; a local Opik does not.
if [ -n "${OPIK_API_KEY:-}" ]; then export OPIK_AUTH_HEADER="Authorization=${OPIK_API_KEY},"; else export OPIK_AUTH_HEADER=""; fi

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }

echo "==> Building and starting n8n"
docker compose up -d --build

echo -n "==> Waiting for n8n"
for _ in $(seq 1 90); do
  if curl -sf "$N8N_URL/healthz/readiness" >/dev/null 2>&1; then echo " ready"; break; fi
  echo -n "."; sleep 2
done
curl -sf "$N8N_URL/healthz/readiness" >/dev/null || { echo "n8n did not come up"; exit 1; }

# n8n ties the session cookie to a browser id; a fixed header stands in for a browser.
COOKIES="$(mktemp)"; trap 'rm -f "$COOKIES"' EXIT
BID="pantry-setup"
SETUP_BODY=$(printf '{"email":"%s","firstName":"Pantry","lastName":"Coordinator","password":"%s"}' "$OWNER_EMAIL" "$OWNER_PASSWORD")
LOGIN_BODY=$(printf '{"emailOrLdapLoginId":"%s","password":"%s"}' "$OWNER_EMAIL" "$OWNER_PASSWORD")

echo "==> Owner account"
authed=""
for _ in $(seq 1 15); do
  if curl -sf -c "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BID" \
       -X POST "$N8N_URL/rest/owner/setup" -d "$SETUP_BODY" >/dev/null 2>&1; then authed=1; break; fi
  if curl -sf -c "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BID" \
       -X POST "$N8N_URL/rest/login" -d "$LOGIN_BODY" >/dev/null 2>&1; then echo "    already claimed, logged in"; authed=1; break; fi
  sleep 2
done
[ -n "$authed" ] || { echo "could not log in to n8n"; exit 1; }

echo "==> n8n API key"
API_KEY=$(curl -sf -b "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BID" \
  -X POST "$N8N_URL/rest/api-keys" \
  -d "{\"label\":\"pantry-setup-$(date +%s)\",\"expiresAt\":null,\"scopes\":[\"workflow:create\",\"workflow:read\",\"workflow:update\",\"workflow:delete\",\"workflow:list\",\"workflow:activate\",\"workflow:deactivate\",\"credential:create\",\"credential:delete\",\"execution:read\",\"execution:list\"]}" \
  | json "['data']['rawApiKey']")

api() {
  if [ -n "${3:-}" ]; then
    curl -sf -X "$1" "$N8N_URL/api/v1$2" -H "X-N8N-API-KEY: $API_KEY" -H 'Content-Type: application/json' -d "$3"
  else
    curl -sf -X "$1" "$N8N_URL/api/v1$2" -H "X-N8N-API-KEY: $API_KEY"
  fi
}

echo "==> OpenAI credential"
CRED_ID=$(api POST /credentials "$(printf '{"name":"OpenAI (volunteer screening)","type":"openAiApi","data":{"apiKey":"%s"}}' "$OPENAI_API_KEY")" | json "['id']")

echo "==> Replacing any earlier copy of the workflow"
api GET "/workflows?name=Food%20bank%20volunteer%20screening" \
  | python3 -c "import json,sys; [print(w['id']) for w in json.load(sys.stdin).get('data',[])]" \
  | while read -r wid; do api DELETE "/workflows/$wid" >/dev/null; echo "    deleted $wid"; done

echo "==> Importing and activating the workflow"
WF_BODY=$(python3 - "$CRED_ID" <<'PY'
import json, sys
wf = json.load(open("workflow/volunteer-screening.json"))
print(json.dumps(wf).replace("__OPENAI_CREDENTIAL_ID__", sys.argv[1]))
PY
)
WF_ID=$(api POST /workflows "$WF_BODY" | json "['id']")
api POST "/workflows/$WF_ID/activate" "" >/dev/null

echo
echo "n8n:      $N8N_URL  (login $OWNER_EMAIL / $OWNER_PASSWORD)"
echo "Webhook:  $N8N_URL/webhook/volunteer-signup"
echo "Next:     ./demo.sh"
