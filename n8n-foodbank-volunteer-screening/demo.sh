#!/usr/bin/env bash
# Post four sample volunteer sign-ups to the webhook and print each screening result.
# Every POST is one workflow execution, which n8n-observability turns into one Opik trace.
set -euo pipefail

WEBHOOK="${WEBHOOK:-http://localhost:5678/webhook/volunteer-signup}"

send() {
  echo "-- $2"
  # The webhook can take a few seconds to register right after activation.
  for _ in $(seq 1 15); do
    if OUT=$(curl -sf -X POST "$WEBHOOK" -H 'Content-Type: application/json' -d "$1"); then
      echo "$OUT" | python3 -m json.tool; echo; return 0
    fi
    sleep 2
  done
  echo "no answer from $WEBHOOK; did setup.sh finish?" >&2
  exit 1
}

send '{"name": "Rosa Delgado", "age": 34,
  "availability": "Saturday mornings",
  "about": "Retired school bus driver, still hold a commercial driving licence. Happy to do deliveries."}' \
  "Rosa Delgado (licensed driver)"

send '{"name": "Owen Park", "age": 16,
  "availability": "Weekday afternoons after school",
  "about": "Need service hours for school. I am strong and fine with lifting boxes."}' \
  "Owen Park (16, wants warehouse)"

send '{"name": "Priya Raman",
  "availability": "Wednesday evenings",
  "about": "I would love to drive deliveries, I have a car."}' \
  "Priya Raman (wants to drive, no age or licence given)"

send '{"name": "Sam Okafor", "age": 19,
  "availability": "Tuesdays 9-12, but only until the end of the month",
  "about": "Studying social work, speak Igbo and English, comfortable talking to clients."}' \
  "Sam Okafor (front desk fit)"

echo "Open the n8n-foodbank-volunteer-screening project in Opik to see one trace per sign-up."
