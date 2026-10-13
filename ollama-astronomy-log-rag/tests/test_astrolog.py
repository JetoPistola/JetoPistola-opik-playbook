import importlib
import sys

import pytest

from astrolog import config
from astrolog.answer import build_chain
from astrolog.cli import DEMO_QUESTIONS, main
from astrolog.ingest import load_chunks
from astrolog.retrieve import make_retriever


def test_ingest_one_chunk_per_entry():
    chunks = load_chunks(config.DOCS_DIR)
    assert len(chunks) == 8
    assert {"source", "entry"} <= set(chunks[0].metadata)
    assert all(c.page_content.startswith("Marlowe Ridge") or "##" in c.page_content for c in chunks)


def test_retrieval_tool_with_tracking_disabled(fake_store):
    # make_retriever returns an @opik.track-decorated function; with
    # OPIK_TRACK_DISABLE=true it still behaves like a plain function.
    search = make_retriever(fake_store)
    out = search("Perseid meteor watch")
    assert "Perseid" in out
    assert out.count("\n\n---\n\n") == config.TOP_K - 1


def test_chain_end_to_end_with_fakes(fake_store, fake_llm):
    chain = build_chain(fake_store)
    assert chain.invoke("How many meteors?") == "47 meteors."


def test_cli_parsing(monkeypatch):
    calls = []
    monkeypatch.setattr("astrolog.cli._run", lambda qs: calls.append(qs))
    monkeypatch.setattr(sys, "argv", ["astrolog", "ask", "Who attended?"])
    main()
    monkeypatch.setattr(sys, "argv", ["astrolog", "demo"])
    main()
    assert calls == [["Who attended?"], DEMO_QUESTIONS]
    monkeypatch.setattr(sys, "argv", ["astrolog"])
    with pytest.raises(SystemExit):
        main()


def test_ingest_command_lists_entries(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["astrolog", "ingest"])
    main()
    assert len(capsys.readouterr().out.strip().splitlines()) == 8


def test_ollama_base_url_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example:9999")
    try:
        assert importlib.reload(config).OLLAMA_BASE_URL == "http://example:9999"
        monkeypatch.delenv("OLLAMA_BASE_URL")
        assert importlib.reload(config).OLLAMA_BASE_URL == "http://localhost:11434"
    finally:
        monkeypatch.undo()
        importlib.reload(config)
