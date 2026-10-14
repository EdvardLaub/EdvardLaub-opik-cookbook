#!/usr/bin/env bash
# Ask the Marigold Lane box-office assistant four patron questions through
# Dify's service API, the same API a theater website widget would call.
# All four share one Dify conversation; with tracing on, Dify reports each
# message to Opik and uses the conversation id as the Opik thread id.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HERE/.dify-state.json"

if [ ! -f "$STATE" ]; then
  echo "No .dify-state.json found. Run ./setup.sh first." >&2
  exit 1
fi

python3 - "$STATE" <<'PY'
import json, sys, urllib.request

state = json.load(open(sys.argv[1]))
url, key = state["dify_url"], state["app_api_key"]

QUESTIONS = [
    "I'm bringing my mum, who uses a wheelchair, to The Lighthouse Keeper's Daughter. Where would we sit and how do I book it?",
    "We bought four adult tickets online for Saturday Oct 17. Something came up on Oct 12. Can we get our money back?",
    "OK, what if we exchange them instead? We would ask today, Oct 12. What would that cost?",
    "Can you quote me a price for a 30-person group booking with a private pre-show reception?",
]

conversation_id = ""  # reuse one conversation so the questions form a thread
for i, q in enumerate(QUESTIONS, 1):
    print(f"\n[{i}/{len(QUESTIONS)}] Patron: {q}")
    req = urllib.request.Request(
        f"{url}/v1/chat-messages",
        data=json.dumps({
            "inputs": {},
            "query": q,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": "demo-patron",
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.load(resp)
    conversation_id = body.get("conversation_id", conversation_id)
    print(f"\nBox office: {body['answer']}")

print("\nDone. Open the 'dify-theater-box-office' project in Opik: Traces for the messages, Threads for the conversation.")
PY
