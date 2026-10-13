"""Boot the API on 127.0.0.1:5302, play scripted conversations over HTTP, shut down."""
import threading
import time

import httpx
import uvicorn

from library_chat import server

PORT = 5302
BASE = f"http://127.0.0.1:{PORT}"

CONVERSATIONS = {
    "patron-cozy-mystery": [
        "Hi! I'm looking for a cozy mystery set somewhere coastal.",
        "Is it on the shelf right now?",
        "What about a mystery with codes or puzzles instead?",
    ],
    "patron-sci-fi-crew": [
        "Any hopeful science fiction about a ship crew?",
        "Something darker and more political, then?",
        "Thanks. Do you have anything on dragons?",
    ],
    "patron-kids-and-cooking": [
        "I need a bedtime picture book for my 4 year old.",
        "And a cheap vegetarian weeknight cookbook for me?",
    ],
    "patron-nature-walks": [
        "I want to learn to identify owls in my backyard.",
        "Any essays about hiking along rivers?",
        "Which of those two is better for a total beginner?",
    ],
}


def main() -> None:
    config = uvicorn.Config(server.app, host="127.0.0.1", port=PORT, log_level="warning")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            if httpx.get(f"{BASE}/health").status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.2)
    else:
        raise SystemExit("server did not start")

    try:
        for cid, turns in CONVERSATIONS.items():
            print(f"\n=== {cid} ===")
            for text in turns:
                r = httpx.post(f"{BASE}/chat", json={"message": text, "conversation_id": cid}, timeout=60)
                r.raise_for_status()
                print(f"Patron: {text}\nDewey:  {r.json()['reply']}\n")
    finally:
        srv.should_exit = True
        thread.join(timeout=10)
        server.flush()
    print(f'Done. Open project "{server.PROJECT_NAME}" in Opik -> Threads.')
