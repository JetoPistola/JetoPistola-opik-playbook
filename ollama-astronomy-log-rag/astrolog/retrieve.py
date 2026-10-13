"""Retrieval over the in-memory vector store, as a plain function."""
from langchain_core.vectorstores import InMemoryVectorStore

from .config import TOP_K


def make_retriever(store: InMemoryVectorStore):
    def search_observing_logs(question: str) -> str:
        docs = store.similarity_search(question, k=TOP_K)
        return "\n\n---\n\n".join(d.page_content for d in docs)

    return search_observing_logs
