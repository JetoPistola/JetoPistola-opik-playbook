#!/usr/bin/env bash
# Ask the Ironleaf front-desk assistant four questions through Dify's service API,
# the way a website chat widget would. One Dify conversation, so Opik groups the
# answers into a single thread in the "dify-gym-membership-assistant" project.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HERE/.dify-state.json"
[ -f "$STATE" ] || { echo "No .dify-state.json yet; run ./setup.sh first." >&2; exit 1; }

python3 - "$STATE" <<'PY'
import json, sys, urllib.request

state = json.load(open(sys.argv[1]))
url, key = state["dify_url"], state["app_api_key"]

QUESTIONS = [
    "I'm a student and only free on weekday afternoons. Which membership should I get and what will it cost me per month?",
    "If I go with that, can I still do the Thursday evening Boxing Fit class?",
    "Can my 14-year-old son come with me to the gym floor or to a class?",
    "I hurt my knee last week. Should I do Gentle Mobility or skip classes for a while?",
]

conversation_id = ""
for i, q in enumerate(QUESTIONS, 1):
    print(f"\n[{i}/{len(QUESTIONS)}] Member: {q}")
    req = urllib.request.Request(
        f"{url}/v1/chat-messages",
        data=json.dumps({"inputs": {}, "query": q, "response_mode": "blocking",
                         "conversation_id": conversation_id, "user": "demo-member"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.load(resp)
    conversation_id = body.get("conversation_id", conversation_id)
    print(f"\nFront desk: {body['answer']}")

print("\nDone. Open the 'dify-gym-membership-assistant' project in Opik.")
PY
