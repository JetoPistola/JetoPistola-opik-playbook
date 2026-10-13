from langchain_core.messages import HumanMessage

from library_chat import server


def test_chain_is_string_in_string_out(prompts):
    reply = server.chain.invoke(
        "cozy mystery please", config={"configurable": {"conversation_id": "t-chain"}}
    )
    assert reply == "stub reply #1"
    assert isinstance(reply, str)
    # The retrieved catalog excerpt reaches the prompt the model sees.
    assert "The Lantern Keeper's Daughter" in prompts[0]


def test_chat_endpoint_returns_reply_and_remembers_history(client, prompts):
    r1 = client.post("/chat", json={"message": "cozy coastal mystery", "conversation_id": "c1"})
    assert r1.status_code == 200
    assert r1.json() == {"reply": "stub reply #1", "conversation_id": "c1"}

    r2 = client.post("/chat", json={"message": "is it on the shelf?", "conversation_id": "c1"})
    assert r2.json()["reply"] == "stub reply #2"
    # Turn two sees turn one in the history, and keeps searching on the earlier topic.
    assert "cozy coastal mystery" in prompts[1]
    assert "stub reply #1" in prompts[1]
    assert "The Lantern Keeper's Daughter" in prompts[1]
    assert [type(m) for m in server.HISTORY["c1"]][0] is HumanMessage
    assert len(server.HISTORY["c1"]) == 4


def test_conversations_do_not_share_memory(client, prompts):
    client.post("/chat", json={"message": "cozy coastal mystery", "conversation_id": "a"})
    client.post("/chat", json={"message": "hello", "conversation_id": "b"})
    assert "cozy coastal mystery" not in prompts[1]


def test_empty_message_is_rejected(client):
    r = client.post("/chat", json={"message": "   ", "conversation_id": "c"})
    assert r.status_code == 400


def test_health(client):
    assert client.get("/health").json() == {"ok": True}
