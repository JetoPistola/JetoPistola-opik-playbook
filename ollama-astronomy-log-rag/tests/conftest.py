"""Offline fixtures: fake embeddings and a fake chat model, so Ollama is never needed."""
import hashlib

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel


class FakeEmbeddings(Embeddings):
    """Bag-of-words hashing into 64 buckets: deterministic, and shared words give similarity."""

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * 64
        for w in text.lower().split():
            v[int(hashlib.md5(w.strip(".,?:").encode()).hexdigest(), 16) % 64] += 1.0
        return v

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def fake_store(monkeypatch):
    from astrolog import store

    monkeypatch.setattr(store, "OllamaEmbeddings", lambda **kw: FakeEmbeddings())
    return store.build_store()


@pytest.fixture
def fake_llm(monkeypatch):
    from astrolog import answer

    monkeypatch.setattr(answer, "ChatOllama", lambda **kw: FakeListChatModel(responses=["47 meteors."]))
