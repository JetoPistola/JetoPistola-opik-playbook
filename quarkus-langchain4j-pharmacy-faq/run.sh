#!/usr/bin/env bash
# Build the app (JVM mode), start it on :5304, ask four scripted questions over HTTP, then
# stop it with SIGTERM so the OpenTelemetry batch processor flushes every span to Opik.
set -euo pipefail
cd "$(dirname "$0")"

# Keys: repo-root .env first, then a local .env.
for env_file in ../.env .env; do
  if [[ -f "$env_file" ]]; then set -a; . "$env_file"; set +a; fi
done
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (see .env.example)}"
export OPIK_OTEL_ENDPOINT="${OPIK_OTEL_ENDPOINT:-http://localhost:5173/api/v1/private/otel}"
export OPIK_WORKSPACE="${OPIK_WORKSPACE:-default}"

MVN=mvn; [[ -x ./mvnw ]] && MVN=./mvnw
$MVN -q package -DskipTests

PORT=5304
java -jar target/quarkus-app/quarkus-run.jar > target/app.log 2>&1 &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null || true' EXIT

echo "Waiting for the app on :$PORT ..."
for _ in $(seq 1 60); do
  # plain TCP probe: an HTTP probe would show up as its own trace in Opik
  (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
  kill -0 "$APP_PID" 2>/dev/null || { echo "app died:"; tail -30 target/app.log; exit 1; }
  sleep 1
done

QUESTIONS=(
  "How should I store Quillavet eye drops once the bottle is opened?"
  "I forgot my Mirrowan syrup dose, what should I do?"
  "Are you open on Sunday, and who do I ask for a private question?"
  "Can I raise my Tormisal dose since my cough is getting worse?"
)
for q in "${QUESTIONS[@]}"; do
  echo; echo "Q: $q"
  printf 'A: '
  curl -sf -G "http://127.0.0.1:$PORT/ask" --data-urlencode "q=$q"
  echo
done

echo; echo "Stopping app so spans flush ..."
kill -TERM "$APP_PID"
wait "$APP_PID" 2>/dev/null || true
trap - EXIT
echo "Done. Open the quarkus-langchain4j-pharmacy-faq project in Opik."
