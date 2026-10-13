"""In-memory vector store backed by local nomic-embed-text embeddings."""
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings

from .config import DOCS_DIR, EMBED_MODEL, OLLAMA_BASE_URL
from .ingest import load_chunks


def build_store() -> InMemoryVectorStore:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    store = InMemoryVectorStore(embeddings)
    store.add_documents(load_chunks(DOCS_DIR))
    return store
